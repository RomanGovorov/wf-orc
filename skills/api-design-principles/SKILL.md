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
  - "**/graphql/**/schema*"
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

### 3. Idempotency

- Idempotent operations: the result is the same on repeated calls
- GET, PUT, DELETE — idempotent
- POST — NOT idempotent (creating a new resource)
- For POST: use an idempotency key (`Idempotency-Key: <uuid>`)

## Patterns

### Pattern 1: Resource Collection Design

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
```

### Pattern 2: Pagination

```python
from typing import Optional
from fastapi import Query
from pydantic import BaseModel

class PaginatedResponse[T](BaseModel):
    items: list[T]
    total: int
    page: int
    page_size: int
    pages: int

@app.get("/api/users", response_model=PaginatedResponse[UserRead])
async def list_users(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status: Optional[str] = Query(None),
):
    total = await count_users(status=status)
    offset = (page - 1) * page_size
    users = await fetch_users(limit=page_size, offset=offset, status=status)
    pages = max(1, (total + page_size - 1) // page_size)
    
    return PaginatedResponse(
        items=users, total=total, page=page, page_size=page_size, pages=pages
    )
```

**Pagination Strategy Matrix:**

| Strategy | When to Use | Example |
|---|---|---|
| Offset/Limit | Simple lists, pagination UI | `?page=2&page_size=20` |
| Cursor (keyset) | Large datasets, infinite scroll | `?cursor=eyJjcmVhdGVkX2F0IjoiLi4uIn0` |

### Pattern 3: Error Handling

```python
from pydantic import BaseModel
from datetime import datetime, timezone

class ErrorResponse(BaseModel):
    error: str               # Machine-readable code
    message: str             # Human-readable description
    details: Optional[dict] = None
    timestamp: str
    path: str

STATUS_CODES = {
    200: "Success", 201: "Created", 204: "No Content",
    400: "Bad Request", 401: "Unauthorized", 403: "Forbidden",
    404: "Not Found", 409: "Conflict", 422: "Validation Error",
    429: "Too Many Requests", 500: "Internal Error"
}

def raise_not_found(resource: str, resource_id: str):
    raise HTTPException(
        status_code=404,
        detail={
            "error": "NotFound",
            "message": f"{resource} not found",
            "details": {"id": resource_id},
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "path": f"/api/{resource}s/{resource_id}"
        }
    )
```

**Status Code Mapping:**

| Code | When to Use |
|---|---|
| 200 | Successful GET/PUT/PATCH/DELETE |
| 201 | Successful POST (resource created) |
| 204 | DELETE with no response body |
| 400 | Bad request — malformed JSON, wrong Content-Type |
| 401 | Not authenticated — no token or expired |
| 403 | Forbidden — no permission |
| 404 | Not found — resource doesn't exist |
| 409 | Conflict — duplicate key, email taken |
| 422 | Validation failed — field-level errors |
| 429 | Rate limit exceeded |
| 500 | Internal server error |

### Pattern 4: API Versioning

```python
from fastapi import APIRouter

# URL versioning (most common)
v1_router = APIRouter(prefix="/api/v1")
v1_router.get("/users")(list_users_v1)

v2_router = APIRouter(prefix="/api/v2")
v2_router.get("/users")(list_users_v2)

app.include_router(v1_router)
app.include_router(v2_router)

# Deprecation headers
@app.middleware("http")
async def add_deprecation_headers(request: Request, call_next):
    response = await call_next(request)
    if "/api/v1/" in request.url.path:
        response.headers["Sunset"] = "Sat, 31 Dec 2026 23:59:59 GMT"
        response.headers["Deprecation"] = "@1798761599"
    return response
```

**When to Version:**
- Breaking changes in response/request structure
- Changing endpoint semantics
- Do NOT version: adding new fields, bug fixes, security fixes

### Pattern 5: Idempotency for POST

```python
import hashlib
import json
import redis.asyncio as redis

redis_client = redis.from_url("redis://localhost:6379")
IDEMPOTENCY_TTL = 24 * 60 * 60  # 24 hours

def _payload_hash(payload: dict) -> str:
    return hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()[:32]

@app.post("/api/payments")
async def create_payment(
    request: Request,
    data: PaymentCreate,
    idempotency_key: str = Header(...),
):
    user_id = request.state.user_id
    scoped = f"idempotency:{user_id}:{idempotency_key}"
    payload_hash = _payload_hash(data.model_dump())
    
    # ATOMIC claim with SET NX
    acquired = await redis_client.set(
        scoped, f"{payload_hash}|pending", nx=True, ex=IDEMPOTENCY_TTL
    )
    if not acquired:
        existing = await redis_client.get(scoped)
        existing_hash, status = existing.split("|", 1)
        if existing_hash != payload_hash:
            raise HTTPException(409, "IdempotencyKeyReuseWithDifferentPayload")
        if status == "pending":
            raise HTTPException(409, "IdempotencyKeyInProgress")
        return json.loads(status.split(":", 1)[1])
    
    try:
        result = await process_payment_impl(data)
    except Exception:
        await redis_client.delete(scoped)
        raise
    
    await redis_client.set(
        scoped, f"{payload_hash}|complete:{json.dumps(result)}", ex=IDEMPOTENCY_TTL
    )
    return result
```

### Pattern 6: GraphQL Schema Design

```graphql
type Query {
  user(id: ID!): User
  users(first: Int = 20, after: String, status: UserStatus): UserConnection!
}

type User {
  id: ID!
  email: String!
  name: String!
  orders(first: Int = 20, after: String): OrderConnection!
}

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
}
```

### Pattern 7: Webhook Design

```python
import hmac
import hashlib

WEBHOOK_SECRET = os.environ["WEBHOOK_SECRET"]

async def send_webhook(url: str, payload: dict, secret: str):
    body = json.dumps(payload).encode()
    signature = hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
    
    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.post(
            url,
            content=body,
            headers={
                "Content-Type": "application/json",
                "X-Webhook-Signature": f"sha256={signature}",
                "X-Webhook-Event": payload.get("event"),
            },
        )
        resp.raise_for_status()

@app.post("/webhooks")
async def receive_webhook(request: Request):
    body = await request.body()
    signature = request.headers.get("X-Webhook-Signature", "")
    expected = f"sha256={hmac.new(WEBHOOK_SECRET.encode(), body, hashlib.sha256).hexdigest()}"
    
    if not hmac.compare_digest(signature, expected):
        raise HTTPException(401, "Invalid signature")
    
    event = json.loads(body)
    asyncio.create_task(process_webhook_event(event))
    return {"received": True}
```

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
10. **Content negotiation** — `Accept: application/json`

## Common Pitfalls

| Mistake | Why It's Bad | Fix |
|---|---|---|
| Action endpoints (`/createUser`) | Not RESTful, doesn't scale | Resource URLs (`POST /users`) |
| Returning `password` in JSON | Security risk | Exclude sensitive fields |
| No pagination | OOM on large tables | Cursor-based or offset pagination |
| No HTTP status codes | Client confused | Correct 2xx/4xx/5xx |
| Breaking changes without versioning | Breaks clients | Versioning or deprecation |
| N+1 queries in GraphQL | Performance | DataLoaders |
| DB schema leak | API tied to DB | API layer abstraction |

## Context7 Integration

When Context7 MCP tools are available, use them to fetch up-to-date library documentation.

| Library | Context7 ID | When to Query |
|---------|-------------|---------------|
| FastAPI | `/websites/fastapi_tiangolo` | REST endpoints, dependencies |
| Express.js | (query "Express.js") | Middleware, routing |
| OpenAPI | (query "OpenAPI Specification") | Schema definition |
| GraphQL | (query "GraphQL") | Schema design, resolvers |
| Zod | `/colinhacks/zod` | Runtime validation |

> **See also**: `python-professional` — FastAPI dependency injection, middleware. `performance-optimization` — N+1 prevention, caching.

## Additional Resources

- **Advanced patterns:** See [`advanced.md`](advanced.md) for deep dives, edge cases, and advanced techniques
- **Code examples:** See [`examples.md`](examples.md) for complete working examples and templates
