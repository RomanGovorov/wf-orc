# Code Examples: API Design Principles

> Working examples for [`SKILL.md`](SKILL.md).

## Example 1: Complete REST API with FastAPI

### Full Application

```python
# main.py
from contextlib import asynccontextmanager
from fastapi import FastAPI
from app.api.router import api_router

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    await init_db()
    yield
    # Shutdown
    await close_db()

app = FastAPI(title="MyAPI", version="1.0.0", lifespan=lifespan)
app.include_router(api_router, prefix="/api/v1")
```

### Router Structure

```python
# app/api/router.py
from fastapi import APIRouter
from app.api.endpoints import users, orders, auth

api_router = APIRouter()
api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(users.router, prefix="/users", tags=["users"])
api_router.include_router(orders.router, prefix="/orders", tags=["orders"])
```

### Users Endpoint

```python
# app/api/endpoints/users.py
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from app.api.deps import get_db, get_current_user
from app.schemas.user import UserCreate, UserRead
from app.services.user_service import UserService

router = APIRouter()

@router.get("/users", response_model=list[UserRead])
async def list_users(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    status: str | None = Query(None, description="Filter by status"),
    db: AsyncSession = Depends(get_db),
):
    """List users with pagination and filtering."""
    service = UserService(db)
    return await service.get_users(page=page, page_size=page_size, status=status)

@router.post("/users", response_model=UserRead, status_code=201)
async def create_user(
    data: UserCreate,
    db: AsyncSession = Depends(get_db),
):
    """Create a new user."""
    service = UserService(db)
    
    # Check for duplicates
    existing = await service.get_user_by_email(data.email)
    if existing:
        raise HTTPException(
            status_code=409,
            detail={
                "error": "Conflict",
                "message": "Email already registered",
                "details": {"email": data.email},
            }
        )
    
    return await service.create_user(data)

@router.get("/users/{user_id}", response_model=UserRead)
async def get_user(
    user_id: int,
    db: AsyncSession = Depends(get_db),
):
    """Get a specific user by ID."""
    service = UserService(db)
    user = await service.get_user(user_id)
    if not user:
        raise HTTPException(
            status_code=404,
            detail={
                "error": "NotFound",
                "message": "User not found",
                "details": {"id": user_id},
            }
        )
    return user

@router.delete("/users/{user_id}", status_code=204)
async def delete_user(
    user_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Delete a user (requires admin role)."""
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin role required")
    
    service = UserService(db)
    await service.delete_user(user_id)
```

## Example 2: Complete Error Handling

### Error Models

```python
# app/schemas/errors.py
from pydantic import BaseModel
from typing import Optional
from datetime import datetime, timezone

class ErrorResponse(BaseModel):
    error: str
    message: str
    details: Optional[dict] = None
    timestamp: str
    path: str

class ValidationErrorDetail(BaseModel):
    field: str
    message: str
    value: str | int | bool | list | None = None

class ValidationErrorResponse(BaseModel):
    error: str = "ValidationError"
    message: str = "Request validation failed"
    details: list[ValidationErrorDetail]
    timestamp: str
    path: str
```

### Error Handlers

```python
# app/core/errors.py
from fastapi import Request, HTTPException
from fastapi.responses import JSONResponse
from datetime import datetime, timezone

@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """Consistent error format across all endpoints."""
    if isinstance(exc.detail, dict):
        body = dict(exc.detail)
        body.setdefault("timestamp", datetime.now(timezone.utc).isoformat())
        body.setdefault("path", str(request.url))
        return JSONResponse(status_code=exc.status_code, content=body)
    
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": "HTTPException",
            "message": str(exc.detail),
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "path": str(request.url),
        },
    )

@app.exception_handler(Exception)
async def generic_exception_handler(request: Request, exc: Exception):
    """Catch-all for unhandled exceptions."""
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={
            "error": "InternalError",
            "message": "An unexpected error occurred",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "path": str(request.url),
        },
    )
```

## Example 3: Complete Pagination Implementation

### Offset Pagination

```python
# app/core/pagination.py
from pydantic import BaseModel
from typing import Generic, TypeVar

T = TypeVar("T")

class PaginatedResponse(BaseModel, Generic[T]):
    items: list[T]
    total: int
    page: int
    page_size: int
    pages: int
    
    @property
    def has_next(self) -> bool:
        return self.page < self.pages
    
    @property
    def has_prev(self) -> bool:
        return self.page > 1

async def paginate(
    query,
    db: AsyncSession,
    page: int = 1,
    page_size: int = 20,
) -> PaginatedResponse:
    """Generic pagination helper."""
    # Count total
    count_query = select(func.count()).select_from(query.subquery())
    total = (await db.execute(count_query)).scalar()
    
    # Apply pagination
    items_query = query.offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(items_query)
    items = list(result.scalars().all())
    
    pages = max(1, (total + page_size - 1) // page_size)
    
    return PaginatedResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        pages=pages,
    )

# Usage
@router.get("/users")
async def list_users(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    query = select(User).order_by(User.created_at.desc())
    return await paginate(query, db, page, page_size)
```

### Cursor Pagination

```python
import base64
import json

def encode_cursor(**kwargs) -> str:
    """Encode cursor from sort key fields."""
    payload = json.dumps(kwargs)
    return base64.urlsafe_b64encode(payload.encode()).decode()

def decode_cursor(cursor: str) -> dict:
    """Decode cursor to sort key fields."""
    try:
        decoded = base64.urlsafe_b64decode(cursor.encode())
        return json.loads(decoded)
    except (ValueError, KeyError, json.JSONDecodeError):
        raise HTTPException(400, detail={"error": "InvalidCursor"})

@router.get("/users/cursor")
async def list_users_cursor(
    limit: int = Query(20, ge=1, le=100),
    cursor: str | None = Query(None),
    db: AsyncSession = Depends(get_db),
):
    """Cursor-based pagination for infinite scroll."""
    after = decode_cursor(cursor) if cursor else None
    
    query = select(User).order_by(User.created_at.desc(), User.id.desc())
    
    if after:
        query = query.where(
            (User.created_at, User.id) < (after["created_at"], after["id"])
        )
    
    query = query.limit(limit + 1)  # Fetch one extra
    result = await db.execute(query)
    rows = list(result.scalars().all())
    
    has_more = len(rows) > limit
    items = rows[:limit]
    
    next_cursor = None
    if has_more and items:
        last = items[-1]
        next_cursor = encode_cursor(
            created_at=last.created_at.isoformat(),
            id=last.id,
        )
    
    return {
        "items": items,
        "next_cursor": next_cursor,
        "has_more": has_more,
    }
```

## Example 4: Complete Idempotency Implementation

```python
# app/core/idempotency.py
import hashlib
import json
import redis.asyncio as redis
from fastapi import Header, HTTPException

redis_client = redis.from_url("redis://localhost:6379")
IDEMPOTENCY_TTL = 24 * 60 * 60  # 24 hours

def _scope_key(user_id: str, key: str) -> str:
    """Scope keys per user to prevent cross-tenant collision."""
    return f"idempotency:{user_id}:{key}"

def _payload_hash(payload: dict) -> str:
    """Deterministic hash of request payload."""
    return hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()[:32]

async def check_idempotency(
    user_id: str,
    idempotency_key: str,
    payload: dict,
) -> dict | None:
    """Check idempotency and return cached response if complete."""
    scoped = _scope_key(user_id, idempotency_key)
    payload_hash = _payload_hash(payload)
    
    # Try to claim atomically
    acquired = await redis_client.set(
        scoped, f"{payload_hash}|pending", nx=True, ex=IDEMPOTENCY_TTL
    )
    
    if not acquired:
        existing = await redis_client.get(scoped)
        existing_hash, status = existing.decode().split("|", 1)
        
        if existing_hash != payload_hash:
            raise HTTPException(
                409,
                detail={"error": "IdempotencyKeyReuseWithDifferentPayload"}
            )
        
        if status == "pending":
            raise HTTPException(409, detail={"error": "IdempotencyKeyInProgress"})
        
        # Complete — return cached response
        if status.startswith("complete:"):
            return json.loads(status.split(":", 1)[1])
    
    return None  # Not cached, proceed with operation

async def complete_idempotency(
    user_id: str,
    idempotency_key: str,
    payload: dict,
    result: dict,
):
    """Mark idempotency key as complete with response."""
    scoped = _scope_key(user_id, idempotency_key)
    payload_hash = _payload_hash(payload)
    
    await redis_client.set(
        scoped,
        f"{payload_hash}|complete:{json.dumps(result)}",
        ex=IDEMPOTENCY_TTL,
    )

async def fail_idempotency(user_id: str, idempotency_key: str):
    """Release idempotency key on failure."""
    scoped = _scope_key(user_id, idempotency_key)
    await redis_client.delete(scoped)

# Usage in endpoint
@router.post("/payments")
async def create_payment(
    request: Request,
    data: PaymentCreate,
    idempotency_key: str = Header(..., alias="Idempotency-Key"),
):
    user_id = request.state.user_id
    
    # Check idempotency
    cached = await check_idempotency(user_id, idempotency_key, data.model_dump())
    if cached:
        return cached
    
    try:
        result = await process_payment(data)
        await complete_idempotency(user_id, idempotency_key, data.model_dump(), result)
        return result
    except Exception:
        await fail_idempotency(user_id, idempotency_key)
        raise
```

## Example 5: Complete GraphQL Schema

### Schema Definition

```graphql
# schema.graphql
type Query {
  user(id: ID!): User
  users(
    first: Int = 20
    after: String
    search: String
    status: UserStatus
  ): UserConnection!
  
  order(id: ID!): Order
  orders(first: Int = 20, after: String): OrderConnection!
}

type Mutation {
  createUser(input: CreateUserInput!): CreateUserPayload!
  updateUser(id: ID!, input: UpdateUserInput!): UpdateUserPayload!
  deleteUser(id: ID!): DeleteUserPayload!
  
  createOrder(input: CreateOrderInput!): CreateOrderPayload!
}

type User {
  id: ID!
  email: String!
  name: String!
  status: UserStatus!
  createdAt: DateTime!
  
  # Relationships
  orders(first: Int = 20, after: String): OrderConnection!
  profile: UserProfile
}

enum UserStatus {
  ACTIVE
  INACTIVE
  SUSPENDED
}

type UserProfile {
  bio: String
  avatarUrl: String
}

type Order {
  id: ID!
  userId: ID!
  total: Decimal!
  status: OrderStatus!
  createdAt: DateTime!
  
  items: [OrderItem!]!
}

type OrderItem {
  productId: ID!
  quantity: Int!
  price: Decimal!
}

enum OrderStatus {
  PENDING
  CONFIRMED
  SHIPPED
  DELIVERED
  CANCELLED
}

# Relay-style pagination
type UserConnection {
  edges: [UserEdge!]!
  pageInfo: PageInfo!
  totalCount: Int!
}

type UserEdge {
  node: User!
  cursor: String!
}

type PageInfo {
  hasNextPage: Boolean!
  hasPreviousPage: Boolean!
  startCursor: String
  endCursor: String
}

# Input types
input CreateUserInput {
  email: String!
  name: String!
  password: String!
}

input UpdateUserInput {
  name: String
  status: UserStatus
}

input CreateOrderInput {
  items: [OrderItemInput!]!
}

input OrderItemInput {
  productId: ID!
  quantity: Int!
}

# Payload types
type CreateUserPayload {
  user: User
  errors: [Error!]
}

type UpdateUserPayload {
  user: User
  errors: [Error!]
}

type DeleteUserPayload {
  success: Boolean!
  errors: [Error!]
}

type CreateOrderPayload {
  order: Order
  errors: [Error!]
}

type Error {
  field: String
  message: String!
}

scalar DateTime
scalar Decimal
```

## Example 6: API Testing

### Pytest with httpx

```python
# tests/test_api.py
import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from app.main import app

@pytest_asyncio.fixture
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c

@pytest_asyncio.fixture(autouse=True)
async def clean_db():
    """Truncate tables before each test."""
    await truncate_all_tables()
    yield

@pytest.mark.asyncio
async def test_create_user(client):
    resp = await client.post(
        "/api/v1/users",
        json={"email": "test@example.com", "name": "Test User"}
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["email"] == "test@example.com"
    assert "id" in data

@pytest.mark.asyncio
async def test_create_user_duplicate(client):
    # Create first user
    await client.post(
        "/api/v1/users",
        json={"email": "test@example.com", "name": "Test"}
    )
    
    # Try to create duplicate
    resp = await client.post(
        "/api/v1/users",
        json={"email": "test@example.com", "name": "Test 2"}
    )
    assert resp.status_code == 409
    assert resp.json()["error"] == "Conflict"

@pytest.mark.asyncio
async def test_pagination(client):
    # Create 25 users
    for i in range(25):
        await client.post(
            "/api/v1/users",
            json={"email": f"user{i}@test.com", "name": f"User {i}"}
        )
    
    # First page
    resp = await client.get("/api/v1/users?page=1&page_size=10")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["items"]) == 10
    assert data["total"] == 25
    assert data["pages"] == 3
    
    # Second page
    resp = await client.get("/api/v1/users?page=2&page_size=10")
    data = resp.json()
    assert len(data["items"]) == 10

@pytest.mark.asyncio
async def test_get_nonexistent_user(client):
    resp = await client.get("/api/v1/users/99999")
    assert resp.status_code == 404
    assert resp.json()["error"] == "NotFound"
```

## Additional Resources

- **Core patterns:** See [`SKILL.md`](SKILL.md) for essential patterns
- **Advanced techniques:** See [`advanced.md`](advanced.md) for deep dives and edge cases
