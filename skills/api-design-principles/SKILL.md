---
name: api-design-principles
description: REST and GraphQL API design patterns — resource design, pagination, versioning, error handling, idempotency. Use when designing new APIs, reviewing specifications, refactoring endpoints.
priority: 5
paths:
  - "**/router*"
  - "**/routes*"
  - "**/api/**"
  - "**/endpoint*"
  - "**/views.py"
  - "**/controllers/**"
  - "**/handlers/**"
  - "**/graphql/**"
  - "**/schema*"
---

# API Design Principles

Template for designing intuitive, scalable APIs. REST and GraphQL patterns, error handling, versioning, pagination.

## When to Use This Skill

- When designing new REST/GraphQL endpoints
- When refactoring existing APIs — improving design
- When creating API design standards / guidelines
- When reviewing specifications before implementation
- When migrating between API paradigms (REST → GraphQL)
- When creating OpenAPI/Swagger documentation

## Core Concepts

### 1. Resource-Oriented Architecture (REST)

**Resources — nouns, not verbs:**

- URL represents a resource hierarchy
- HTTP methods define the action
- Naming: `/api/users`, `/api/users/{id}/orders`

**HTTP Methods Semantics:**

| Method | Action | Idempotent | Safe |
|---|---|---|---|
| GET | Retrieve a resource | ✓ | ✓ |
| POST | Create a resource | ✗ | ✗ |
| PUT | Replace a resource entirely | ✓ | ✗ |
| PATCH | Partial update | ✗ | ✗ |
| DELETE | Delete a resource | ✓ | ✗ |

### 2. Statelessness

Each request contains all necessary information:
- No server state between requests
- Authentication in each request (JWT, session cookie)
- Simplifies horizontal scaling

### 3. HATEOAS (Hypermedia as the Engine of Application State)

Responses contain links to related resources — the client navigates the API without knowing the URL structure.

### 4. Idempotency

- Idempotent operations: the result is the same on repeated calls
- GET, PUT, DELETE — idempotent
- POST — NOT idempotent (creating a new resource)
- For POST: use an idempotency key (`Idempotency-Key: <uuid>`)

## Patterns

### REST API Design Patterns

#### Pattern 1: Resource Collection Design

```python
# ✅ GOOD: Resource-oriented endpoints
GET    /api/users                # List users (paginated)
POST   /api/users                # Create user
GET    /api/users/{id}           # Get specific user
PUT    /api/users/{id}           # Replace user
PATCH  /api/users/{id}           # Update user fields
DELETE /api/users/{id}           # Delete user

# Nested resources
GET    /api/users/{id}/orders    # Get user's orders
POST   /api/users/{id}/orders    # Create order for user

# ❌ BAD: Action-oriented endpoints (avoid)
POST   /api/createUser
POST   /api/getUserById
POST   /api/deleteUser
POST   /api/updateUser
GET    /api/getUserOrders?id=123
```

#### Pattern 2: Pagination and Filtering

```python
from fastapi import FastAPI, Query, Depends
from pydantic import BaseModel
from typing import Optional

app = FastAPI()

class PaginatedResponse[T](BaseModel):
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

class UserCursorResponse(BaseModel):
    """Cursor-based pagination (recommended for large datasets)."""
    items: list[dict]
    next_cursor: Optional[str]  # Base64 encoded offset
    has_more: bool

@app.get("/api/users", response_model=PaginatedResponse)
async def list_users(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    status: Optional[str] = Query(None, description="Filter by status"),
    search: Optional[str] = Query(None, description="Search by name/email"),
):
    """
    List users with offset pagination.

    - page_size max: 100 (prevent abuse)
    - status: active, inactive, suspended
    - search: partial match on name or email
    """
    total = await count_users(status=status, search=search)
    offset = (page - 1) * page_size
    users = await fetch_users(
        limit=page_size,
        offset=offset,
        status=status,
        search=search
    )
    pages = max(1, (total + page_size - 1) // page_size)

    return PaginatedResponse(
        items=users,
        total=total,
        page=page,
        page_size=page_size,
        pages=pages
    )
```

**Pagination Strategy Matrix:**

| Strategy | When to Use | Example |
|---|---|---|
| Offset/Limit | Simple lists, pagination UI | `?page=2&page_size=20` |
| Cursor-based | Large datasets, infinite scroll | `?cursor=eyJpZCI6MTAwfQ` |
| Keyset | High performance | `?after_id=42&limit=20` |

#### Pattern 3: Error Handling and Status Codes

```python
from fastapi import HTTPException, status
from pydantic import BaseModel
from datetime import datetime, timezone

class ErrorResponse(BaseModel):
    error: str               # Machine-readable code
    message: str             # Human-readable description
    details: Optional[dict]  # Additional context
    timestamp: str
    path: str

class ValidationErrorDetail(BaseModel):
    field: str
    message: str
    value: Optional[str]

class ValidationErrorResponse(BaseModel):
    error: str = "ValidationError"
    message: str = "Request validation failed"
    details: list[ValidationErrorDetail]
    timestamp: str
    path: str

# ✅ GOOD: Consistent error responses
STATUS_CODES = {
    "success": 200,
    "created": 201,
    "accepted": 202,
    "no_content": 204,
    "bad_request": 400,
    "unauthorized": 401,
    "forbidden": 403,
    "not_found": 404,
    "conflict": 409,
    "unprocessable": 422,
    "too_many_requests": 429,
    "internal_error": 500,
    "bad_gateway": 502,
    "service_unavailable": 503
}

def raise_not_found(resource: str, resource_id: str):
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail={
            "error": "NotFound",
            "message": f"{resource} not found",
            "details": {"id": resource_id},
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "path": f"/api/{resource}s/{resource_id}"
        }
    )

def raise_validation_error(errors: list[ValidationErrorDetail], path: str):
    raise HTTPException(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        detail={
            "error": "ValidationError",
            "message": "Request validation failed",
            "details": errors,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "path": path
        }
    )

def raise_conflict(message: str, path: str = ""):
    raise HTTPException(
        status_code=status.HTTP_409_CONFLICT,
        detail={
            "error": "Conflict",
            "message": message,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "path": path,
        }
    )

# FastAPI automatically serializes errors in Pydantic validation
@app.post("/api/users", response_model=UserResponse,
          responses={
              409: {"model": ErrorResponse, "description": "Email already exists"},
              422: {"model": ValidationErrorResponse, "description": "Validation error"}
          })
async def create_user(data: UserCreate):
    existing = await find_user_by_email(data.email)
    if existing:
        raise_conflict("Email already registered")
    return await create_user_impl(data)
```

**Status Code Mapping:**

| Code | When to Use |
|---|---|
| 200 | Successful GET/PUT/PATCH/DELETE |
| 201 | Successful POST (resource created) |
| 204 | DELETE with no response body |
| 400 | Bad request — malformed data failed Pydantic validation |
| 401 | Not authenticated — no token or token expired |
| 403 | Forbidden — no permission for this resource |
| 404 | Not found — resource does not exist |
| 409 | Conflict — email already taken, duplicate key |
| 422 | Validation failed — field-level errors |
| 429 | Rate limit exceeded |
| 500 | Internal server error |

#### Pattern 4: API Versioning

```python
# Strategy 1: URL versioning (most common)
# /api/v1/users
# /api/v2/users

# Strategy 2: Header versioning
# Accept: application/vnd.myapi+json; version=1

# Strategy 3: Query parameter versioning
# /api/users?version=1

# ✅ GOOD: URL versioning with FastAPI
from fastapi import APIRouter

# Version 1 — existing
v1_router = APIRouter(prefix="/api/v1")
v1_router.get("/users")(list_users_v1)
v1_router.get("/users/{id}")(get_user_v1)

# Version 2 — breaking changes
v2_router = APIRouter(prefix="/api/v2")
v2_router.get("/users")(list_users_v2)  # e.g., different response structure

app.include_router(v1_router)
app.include_router(v2_router)

# Version deprecation headers
@app.middleware("http")
async def add_deprecation_headers(request: Request, call_next):
    response = await call_next(request)
    if "/api/v1/" in request.url.path:
        response.headers["Sunset"] = "2026-12-31T23:59:59Z"
        response.headers["Deprecation"] = "true"
    return response
```

**When to Version:**
- Breaking changes in response structure (fields removed, type changed)
- Breaking changes in request structure (new required fields)
- Changing endpoint semantics
- Do NOT version: adding new fields, bug fixes, security fixes

#### Pattern 5: Idempotency for POST

```python
from fastapi import Header, HTTPException
import hashlib
import json

class IdempotencyStore:
    """Store idempotency keys and their responses."""

    def __init__(self):
        self._store: dict[str, dict] = {}  # In production, use Redis/DB

    def check(self, key: str) -> Optional[dict]:
        return self._store.get(key)

    def store(self, key: str, response: dict):
        self._store[key] = response

idempotency_store = IdempotencyStore()

async def get_idempotency_key(
    idempotency_key: str = Header(None, alias="Idempotency-Key")
):
    return idempotency_key

@app.post("/api/payments")
async def create_payment(
    data: PaymentCreate,
    idempotency_key: Optional[str] = Depends(get_idempotency_key)
):
    if not idempotency_key:
        raise HTTPException(
            status_code=400,
            detail={"error": "IdempotencyKeyRequired"}
        )

    # Check if key already exists
    existing = idempotency_store.check(idempotency_key)
    if existing:
        return existing  # Return cached response

    # Process payment
    result = await process_payment_impl(data)

    # Cache response
    idempotency_store.store(idempotency_key, result)

    return result
```

### GraphQL Design Patterns

#### Pattern 1: Schema Design

```graphql
type Query {
  user(id: ID!): User
  users(
    first: Int = 20
    after: String
    search: String
    status: UserStatus
  ): UserConnection!
}

type User {
  id: ID!
  email: String!
  name: String!
  createdAt: DateTime!

  # Relationships
  orders(first: Int = 20, after: String): OrderConnection!
  profile: UserProfile
}

# Relay-style cursor pagination
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

type Mutation {
  createUser(input: CreateUserInput!): CreateUserPayload!
  updateUser(input: UpdateUserInput!): UpdateUserPayload!
}

input CreateUserInput {
  email: String!
  name: String!
  password: String!
}

type CreateUserPayload {
  user: User
  errors: [Error!]
}

type Error {
  field: String
  message: String!
}
```

#### Pattern 2: DataLoader (N+1 Problem)

```python
# pip install aiodataloader
from aiodataloader import DataLoader

class UserLoader(DataLoader):
    """Batch load users by ID — prevents N+1 queries."""

    async def batch_load_fn(self, user_ids: list[str]) -> list:
        # Single query for all requested users
        users = await fetch_users_by_ids(user_ids)
        user_map = {user["id"]: user for user in users}
        return [user_map.get(uid) for uid in user_ids]

class OrdersByUserLoader(DataLoader):
    """Batch load orders by user ID."""

    async def batch_load_fn(self, user_ids: list[str]) -> list:
        orders = await fetch_orders_by_user_ids(user_ids)
        orders_by_user = {}
        for order in orders:
            orders_by_user.setdefault(order["user_id"], []).append(order)
        return [orders_by_user.get(uid, []) for uid in user_ids]

# GraphQL context setup
def create_context():
    return {
        "loaders": {
            "user": UserLoader(),
            "orders_by_user": OrdersByUserLoader()
        }
    }
```

### Express.js API Patterns

#### Router with Zod Validation
```typescript
import { Router } from 'express';
import { z } from 'zod';
import { validate } from '../middleware/validate';

const router = Router();

const CreateUserSchema = z.object({
  email: z.string().email(),
  name: z.string().min(1).max(100),
});

const PaginationSchema = z.object({
  page: z.coerce.number().int().positive().default(1),
  limit: z.coerce.number().int().min(1).max(100).default(20),
  cursor: z.string().optional(),
});

// List with cursor-based pagination
router.get('/users', validate({ query: PaginationSchema }), async (req, res) => {
  const { page, limit, cursor } = req.query;
  const users = await db.user.findMany({
    take: limit,
    skip: cursor ? undefined : (page - 1) * limit,
    cursor: cursor ? { id: cursor } : undefined,
    orderBy: { createdAt: 'desc' },
  });

  res.json({
    data: users,
    pagination: {
      nextCursor: users.length === limit ? users[users.length - 1].id : null,
      hasMore: users.length === limit,
    },
  });
});

router.post('/users', validate({ body: CreateUserSchema }), async (req, res) => {
  const user = await db.user.create({ data: req.body });
  res.status(201).json(user);
});
```

#### Error Handling Middleware
```typescript
import { Request, Response, NextFunction } from 'express';

class AppError extends Error {
  constructor(
    public statusCode: number,
    public code: string,
    message: string,
    public details?: Record<string, string[]>
  ) {
    super(message);
  }
}

const errorHandler = (err: Error, req: Request, res: Response, next: NextFunction) => {
  if (err instanceof AppError) {
    return res.status(err.statusCode).json({
      error: { code: err.code, message: err.message, details: err.details },
    });
  }
  // Unknown errors
  console.error('Unhandled error:', err);
  res.status(500).json({
    error: { code: 'INTERNAL_ERROR', message: 'An unexpected error occurred' },
  });
};
```

### Webhook Design
```python
import os
import hmac
import hashlib
import json
import uuid

from fastapi import FastAPI, Request, HTTPException
import httpx
import asyncio

app = FastAPI()

WEBHOOK_SECRET = os.environ["WEBHOOK_SECRET"]

# Webhook sender
async def send_webhook(url: str, payload: dict, secret: str):
    """Send webhook with HMAC signature and retry logic."""
    body = json.dumps(payload).encode()
    signature = hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()

    async with httpx.AsyncClient(timeout=10) as client:
        for attempt in range(3):
            try:
                resp = await client.post(
                    url,
                    content=body,
                    headers={
                        "Content-Type": "application/json",
                        "X-Webhook-Signature": f"sha256={signature}",
                        "X-Webhook-Event": payload.get("event", "unknown"),
                        "X-Webhook-ID": str(uuid.uuid4()),
                    },
                )
                if resp.status_code < 300:
                    return
            except httpx.TimeoutException:
                if attempt == 2:
                    raise
                await asyncio.sleep(2 ** attempt)

# Webhook receiver — verify signature
@app.post("/webhooks")
async def receive_webhook(request: Request):
    body = await request.body()
    signature = request.headers.get("X-Webhook-Signature", "")
    expected = f"sha256={hmac.new(WEBHOOK_SECRET.encode(), body, hashlib.sha256).hexdigest()}"

    if not hmac.compare_digest(signature, expected):
        raise HTTPException(401, "Invalid signature")

    event = json.loads(body)
    # Process event asynchronously
    # NOTE: create_task is fire-and-forget — unhandled exceptions are silently lost,
    # and tasks may be cancelled on shutdown. For production, use a background worker
    # (e.g., Celery, ARQ) or BackgroundTasks for graceful shutdown support.
    asyncio.create_task(process_webhook_event(event))
    return {"received": True}
```

### Long-Running Operations (202 Accepted)
```python
from fastapi import FastAPI, BackgroundTasks
from pydantic import BaseModel

class ExportRequest(BaseModel):
    format: str  # csv, xlsx, pdf
    filters: dict

class ExportStatus(BaseModel):
    id: str
    status: str  # pending, processing, completed, failed
    progress: float  # 0.0 - 1.0
    download_url: str | None = None

@app.post("/exports", status_code=202)
async def create_export(req: ExportRequest, bg: BackgroundTasks):
    export_id = str(uuid.uuid4())
    # Store initial status
    await store_export_status(export_id, "pending", 0.0)
    # Process in background
    bg.add_task(run_export, export_id, req)
    return ExportStatus(id=export_id, status="pending", progress=0.0)

@app.get("/exports/{export_id}")
async def get_export_status(export_id: str):
    status = await get_export_status(export_id)
    if not status:
        raise HTTPException(404, "Export not found")
    return status

# Client polls until completed
# GET /exports/{id} → {"status": "processing", "progress": 0.5}
# GET /exports/{id} → {"status": "completed", "download_url": "/downloads/abc123.xlsx"}
```

### API Testing (httpx AsyncClient)
```python
import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from app.main import app

@pytest_asyncio.fixture
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c

@pytest.mark.asyncio
async def test_create_and_get_user(client):
    # Create
    resp = await client.post("/users", json={"email": "test@example.com", "name": "Test"})
    assert resp.status_code == 201
    user_id = resp.json()["id"]

    # Get
    resp = await client.get(f"/users/{user_id}")
    assert resp.status_code == 200
    assert resp.json()["email"] == "test@example.com"

@pytest.mark.asyncio
async def test_pagination(client):
    # Create 25 users
    for i in range(25):
        await client.post("/users", json={"email": f"user{i}@test.com", "name": f"User {i}"})

    # First page
    resp = await client.get("/users?limit=10")
    data = resp.json()
    assert len(data["items"]) == 10
    assert data["total"] == 25
    cursor = data["next_cursor"]

    # Second page
    resp = await client.get(f"/users?limit=10&cursor={cursor}")
    assert len(resp.json()["items"]) == 10
```

> **See also**: `python-professional` — FastAPI dependency injection, middleware, lifespan patterns. `performance-optimization` — N+1 query prevention, caching strategies, connection pooling.

## Best Practices

1. **Plural nouns for collections** — `/users` not `/user`
2. **Stateless operations** — each request contains everything needed
3. **Consistent error format** — `error`, `message`, `details`, `timestamp`
4. **Version API from day one** — plan for breaking changes
5. **Pagination for large collections** — max page_size = 100
6. **Response filtering** — `?fields=id,name,email` for large resources
7. **Rate limiting** — protect API from abuse
8. **OpenAPI/Swagger** — interactive documentation
9. **CORS restricted** — not `Access-Control-Allow-Origin: *`
10. **Content negotiation** — `Accept: application/json`, `Accept-Language`

## Common Pitfalls

| Mistake | Why It's Bad | Fix |
|---|---|---|
| Action endpoints (`/createUser`) | Not RESTful, does not scale | Resource URLs (`POST /users`) |
| Returning `password` in JSON | Security risk | Exclude sensitive fields |
| No pagination | OOM on large tables | Cursor-based or offset pagination |
| Not specifying HTTP status codes | Client does not understand the result | Correct 2xx/4xx/5xx |
| Breaking changes without versioning | Breaks clients | Versioning or deprecation |
| N+1 queries in GraphQL | Performance | DataLoaders |
| `DELETE /users/{id}` returns 200 OK with body | Confusing | 204 No Content or 200 with body (choose one style) |
| DB schema leak | API tied to DB | API layer abstraction |

## Context7 Integration

When working with API patterns, verify against current documentation:

| Library | Context7 ID | When to Query |
|---------|-------------|---------------|
| FastAPI | `/websites/fastapi_tiangolo` | REST endpoints, dependencies |
| Express.js | (query "Express.js") | Middleware, routing |
| OpenAPI | (query "OpenAPI Specification") | Schema definition |
| GraphQL | (query "GraphQL") | Schema design, resolvers |
| Zod | `/colinhacks/zod` | Runtime validation |

Use `mcp__context7__resolve-library-id` then `mcp__context7__query-docs` to get current examples.
