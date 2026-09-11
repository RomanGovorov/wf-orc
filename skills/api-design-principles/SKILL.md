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
import base64
import json
from typing import Optional

from fastapi import FastAPI, Query
from pydantic import BaseModel

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
    """Cursor-based pagination (recommended for large datasets).

    The cursor is an OPAQUE base64 of the last row's sort-key POSITION
    (keyset), e.g. {"created_at": ..., "id": ...} — NEVER an offset.
    Offsets drift when rows are inserted/deleted and force the DB to scan
    and skip; a keyset cursor is stable and served by an index seek.
    """
    items: list[dict]
    next_cursor: Optional[str]  # base64 keyset position — opaque to clients
    has_more: bool

def encode_cursor(created_at: str, id_: str) -> str:
    """Cursor = base64 of the sort-key position (keyset), NOT an offset."""
    payload = json.dumps({"created_at": created_at, "id": id_})
    return base64.urlsafe_b64encode(payload.encode()).decode()

def decode_cursor(cursor: str) -> tuple[str, str]:
    try:
        decoded = base64.urlsafe_b64decode(cursor.encode())
        data = json.loads(decoded)
        return data["created_at"], data["id"]
    except (ValueError, KeyError, json.JSONDecodeError):
        raise HTTPException(400, detail={"error": "InvalidCursor"})

class UserRead(BaseModel):
    id: int
    email: str
    name: str
    status: str = "active"

@app.get("/api/users", response_model=PaginatedResponse[UserRead])
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

@app.get("/api/users/cursor", response_model=UserCursorResponse)
async def list_users_cursor(
    limit: int = Query(20, ge=1, le=100, description="Items per page"),
    cursor: Optional[str] = Query(None, description="Opaque cursor from next_cursor"),
):
    """
    List users with cursor (keyset) pagination.

    Fetch limit+1 rows to compute has_more without COUNT(*):
      WHERE (created_at, id) > (:c_ts, :c_id)  -- keyset seek; omit on first page
      ORDER BY created_at, id
      LIMIT :limit_plus_one
    """
    after = decode_cursor(cursor) if cursor else None
    rows = await fetch_users_keyset(after=after, limit=limit + 1)

    has_more = len(rows) > limit
    items = rows[:limit]
    next_cursor = (
        encode_cursor(items[-1]["created_at"], items[-1]["id"])
        if has_more and items else None
    )
    return UserCursorResponse(items=items, next_cursor=next_cursor, has_more=has_more)
```

**Pagination Strategy Matrix:**

| Strategy | When to Use | Example |
|---|---|---|
| Offset/Limit | Simple lists, pagination UI | `?page=2&page_size=20` |
| Cursor (keyset-encoded) | Large datasets, infinite scroll, high performance | `?cursor=eyJjcmVhdGVkX2F0IjoiLi4uIiwiaWQiOi4uLn0` |

#### Pattern 3: Error Handling and Status Codes

```python
from typing import Optional

from fastapi import HTTPException, Request, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from datetime import datetime, timezone

class ErrorResponse(BaseModel):
    error: str               # Machine-readable code
    message: str             # Human-readable description
    details: Optional[dict] = None  # Additional context (default None so callers can omit)
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

@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """Unwrap HTTPException.detail so the wire format matches the documented schema.

    FastAPI's default handler wraps `detail` in `{"detail": ...}`, but our
    `responses={409: {"model": ErrorResponse}}` documents top-level fields.
    This handler returns the detail dict directly so the wire format matches.
    """
    if isinstance(exc.detail, dict):
        body = dict(exc.detail)  # copy to avoid mutating the original
        body.setdefault("details", None)
        body.setdefault("timestamp", datetime.now(timezone.utc).isoformat())
        body.setdefault("path", str(request.url))
        return JSONResponse(status_code=exc.status_code, content=body)
    # Plain string detail (e.g., FastAPI's built-in 404 for unknown routes)
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": "HTTPException",
            "message": str(exc.detail),
            "details": None,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "path": str(request.url),
        },
    )

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

def raise_conflict(message: str, path: str = "", details: dict | None = None):
    raise HTTPException(
        status_code=status.HTTP_409_CONFLICT,
        detail={
            "error": "Conflict",
            "message": message,
            "details": details,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "path": path,
        }
    )

# FastAPI automatically serializes errors in Pydantic validation
@app.post("/api/users", response_model=UserRead,
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
| 400 | Bad request — malformed request itself: invalid JSON syntax, wrong Content-Type, unparseable payload |
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
from fastapi import APIRouter, Request

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
        # RFC 8594 (Sunset) uses HTTP-date; RFC 9745 (Deprecation) uses Structured Field Date (@ + Unix epoch per RFC 9651 §3.3.7)
        response.headers["Sunset"] = "Sat, 31 Dec 2026 23:59:59 GMT"
        response.headers["Deprecation"] = "@1798761599"
    return response
```

**When to Version:**
- Breaking changes in response structure (fields removed, type changed)
- Breaking changes in request structure (new required fields)
- Changing endpoint semantics
- Do NOT version: adding new fields, bug fixes, security fixes

#### Pattern 5: Idempotency for POST

```python
from typing import Optional
import hashlib
import json

import redis.asyncio as redis
from fastapi import Depends, Header, HTTPException, Request

# Idempotency requires ATOMICITY (Redis SET NX or DB transaction).
# In-memory dict is NOT safe — concurrent retries on a timed-out POST /payments
# will both pass the `if key not in store:` check and double-charge the customer.
# Use Redis for production; the in-memory stub below is labeled for tests only.

redis_client: redis.Redis = redis.from_url("redis://localhost:6379")
IDEMPOTENCY_TTL = 24 * 60 * 60  # 24 hours

def _scope_key(user_id: str, key: str) -> str:
    """Scope keys per authenticated user to prevent cross-tenant collision."""
    return f"idempotency:{user_id}:{key}"

def _payload_hash(payload: dict) -> str:
    """Deterministic hash of the request payload — same input → same hash."""
    return hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()[:32]

async def get_idempotency_key(
    idempotency_key: str = Header(None, alias="Idempotency-Key")
):
    return idempotency_key

@app.post("/api/payments")
async def create_payment(
    request: Request,
    data: PaymentCreate,
    idempotency_key: Optional[str] = Depends(get_idempotency_key),
):
    if not idempotency_key:
        raise HTTPException(status_code=400, detail={"error": "IdempotencyKeyRequired"})

    user_id = request.state.user_id  # set by auth middleware
    scoped = _scope_key(user_id, idempotency_key)
    payload_hash = _payload_hash(data.model_dump())
    entry = f"{payload_hash}|pending"  # or "complete|<json>"

    # ATOMIC claim: SET NX fails if the key already exists (another request claimed it).
    acquired = await redis_client.set(scoped, entry, nx=True, ex=IDEMPOTENCY_TTL)
    if not acquired:
        existing = await redis_client.get(scoped)
        existing_hash, status = existing.split("|", 1)
        if existing_hash != payload_hash:
            # Same key, different payload → caller bug; do NOT return cached response.
            raise HTTPException(
                status_code=409,
                detail={"error": "IdempotencyKeyReuseWithDifferentPayload"},
            )
        if status == "pending":
            # Another request is still processing; tell client to retry.
            raise HTTPException(status_code=409, detail={"error": "IdempotencyKeyInProgress"})
        # status == "complete" → return cached response body.
        return json.loads(status.split(":", 1)[1]) if status.startswith("complete:") else None

    try:
        result = await process_payment_impl(data)
    except Exception:
        # Release the key so the caller can retry.
        await redis_client.delete(scoped)
        raise

    # Mark complete with the response body.
    await redis_client.set(
        scoped,
        f"{payload_hash}|complete:{json.dumps(result)}",
        ex=IDEMPOTENCY_TTL,
    )
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
  email: z.email(), // Zod 4 top-level format check (Zod 3 codebases: z.string().email())
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
  const take = Number(limit) + 1; // fetch one extra to detect hasMore without a COUNT
  const users = await db.user.findMany({
    take,
    skip: cursor ? 1 : undefined, // Prisma cursor is inclusive — skip the boundary row to avoid returning it twice
    cursor: cursor ? { id: String(cursor) } : undefined,
    orderBy: { createdAt: 'desc' },
  });

  const hasMore = users.length > Number(limit);
  const items = users.slice(0, Number(limit));

  res.json({
    data: items,
    pagination: {
      nextCursor: hasMore && items.length > 0 ? items[items.length - 1].id : null,
      hasMore,
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
import asyncio
import hashlib
import hmac
import json
import logging
import os
import uuid

from fastapi import FastAPI, Request, HTTPException
import httpx

app = FastAPI()

WEBHOOK_SECRET = os.environ["WEBHOOK_SECRET"]

logger = logging.getLogger(__name__)

class WebhookDeliveryError(Exception):
    """Raised when a webhook could not be delivered after all retries."""

# Permanent 4xx statuses that should NOT be retried — the receiver will never
# accept this event. Retrying these wastes quota and delays the dead-letter queue.
_RETRYABLE_STATUSES = {408, 425, 429, 500, 502, 503, 504}

# Webhook sender
async def send_webhook(url: str, payload: dict, secret: str, max_attempts: int = 3):
    """Send webhook with HMAC signature and retry logic.

    Design choice: on final failure LOG and RAISE WebhookDeliveryError —
    silently returning None loses events (webhook delivery is usually
    contractual). The caller must handle it: dead-letter queue, alert, or a
    scheduled re-delivery job.

    Retries use exponential backoff on retryable failures (timeouts,
    connection errors, 408/425/429/5xx responses). Permanent 4xx errors
    (401, 403, 404, 410, 422, etc.) are dead-lettered immediately —
    retrying a broken endpoint wastes quota and delays the DLQ.
    """
    body = json.dumps(payload).encode()
    signature = hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
    # Stable across retries so the receiver can dedupe re-delivered events
    webhook_id = str(uuid.uuid4())

    last_error: Exception | None = None
    async with httpx.AsyncClient(timeout=10) as client:
        for attempt in range(max_attempts):
            try:
                resp = await client.post(
                    url,
                    content=body,
                    headers={
                        "Content-Type": "application/json",
                        "X-Webhook-Signature": f"sha256={signature}",
                        "X-Webhook-Event": payload.get("event", "unknown"),
                        "X-Webhook-ID": webhook_id,
                    },
                )
                if resp.status_code < 300:
                    return
                if resp.status_code not in _RETRYABLE_STATUSES:
                    # Permanent 4xx — dead-letter immediately, no retry
                    logger.error(
                        "webhook to %s got permanent HTTP %d — dead-lettering without retry",
                        url, resp.status_code,
                    )
                    raise WebhookDeliveryError(
                        f"receiver returned permanent error HTTP {resp.status_code}"
                    )
                last_error = WebhookDeliveryError(
                    f"receiver returned HTTP {resp.status_code}"
                )
            except httpx.TransportError as exc:  # covers TimeoutException
                last_error = exc
            logger.warning(
                "webhook attempt %d/%d to %s failed: %s",
                attempt + 1, max_attempts, url, last_error,
            )
            if attempt < max_attempts - 1:
                await asyncio.sleep(2 ** attempt)  # backoff before EVERY retry
    raise WebhookDeliveryError(
        f"webhook to {url} failed after {max_attempts} attempts"
    ) from last_error

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
import uuid

from fastapi import BackgroundTasks, FastAPI, HTTPException
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
    # Read from the same store the background task WRITES to
    # (store_export_status / EXPORTS). The storage lookup has a distinct
    # name — calling get_export_status here would be infinite recursion.
    status = await load_export_status(export_id)
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

@pytest_asyncio.fixture(autouse=True)
async def clean_store():
    """Truncate the user store before each test — tests must not share state."""
    await truncate_users()
    yield

@pytest.mark.asyncio
async def test_create_and_get_user(client):
    # Create — use the same /api/users path as the real endpoints
    resp = await client.post("/api/users", json={"email": "test@example.com", "name": "Test"})
    assert resp.status_code == 201
    user_id = resp.json()["id"]

    # Get
    resp = await client.get(f"/api/users/{user_id}")
    assert resp.status_code == 200
    assert resp.json()["email"] == "test@example.com"

@pytest.mark.asyncio
async def test_pagination(client):
    # Create 25 users (clean_store ensures isolation from other tests)
    for i in range(25):
        await client.post("/api/users", json={"email": f"user{i}@test.com", "name": f"User {i}"})

    # First page — the cursor endpoint documented in Pattern 2
    resp = await client.get("/api/users/cursor?limit=10")
    data = resp.json()
    assert len(data["items"]) >= 10  # use >= so leftover rows don't break the assertion
    assert data["has_more"] is True
    cursor = data["next_cursor"]

    # Second page — send the opaque cursor back verbatim
    resp = await client.get(f"/api/users/cursor?limit=10&cursor={cursor}")
    data = resp.json()
    assert len(data["items"]) >= 10
    assert data["has_more"] is True

    # Third page — remaining rows (exactly 5 with a clean store)
    resp = await client.get(f"/api/users/cursor?limit=10&cursor={data['next_cursor']}")
    data = resp.json()
    assert len(data["items"]) >= 1
    assert data["has_more"] is False or data.get("next_cursor") is None
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

When Context7 MCP tools are available in your session, use them to fetch up-to-date library documentation instead of relying on memory. Tool names vary by installation (e.g. `mcp__context7__resolve-library-id` / `mcp__context7__query-docs`, or plugin-prefixed variants such as `mcp__plugin_context7_context7__*`) — check the available-tools listing for the exact names. Always resolve the library ID first; the IDs in the table below are examples and may change.

| Library | Context7 ID | When to Query |
|---------|-------------|---------------|
| FastAPI | `/websites/fastapi_tiangolo` | REST endpoints, dependencies |
| Express.js | (query "Express.js") | Middleware, routing |
| OpenAPI | (query "OpenAPI Specification") | Schema definition |
| GraphQL | (query "GraphQL") | Schema design, resolvers |
| Zod | `/colinhacks/zod` | Runtime validation |
