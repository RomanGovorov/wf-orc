# Advanced Patterns: API Design Principles

> This file extends [`SKILL.md`](SKILL.md) with advanced patterns and edge cases.

## Advanced Pagination: Cursor (Keyset) Implementation

```python
import base64
import json

class UserCursorResponse(BaseModel):
    """Cursor-based pagination for large datasets.
    
    The cursor is an OPAQUE base64 of the last row's sort-key POSITION
    (keyset), e.g. {"created_at": ..., "id": ...} — NEVER an offset.
    Offsets drift when rows are inserted/deleted and force the DB to scan
    and skip; a keyset cursor is stable and served by an index seek.
    """
    items: list[dict]
    next_cursor: Optional[str]
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

@app.get("/api/users/cursor", response_model=UserCursorResponse)
async def list_users_cursor(
    limit: int = Query(20, ge=1, le=100),
    cursor: Optional[str] = Query(None),
):
    """
    Fetch limit+1 rows to compute has_more without COUNT(*):
      WHERE (created_at, id) > (:c_ts, :c_id)  -- keyset seek
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

**Why cursor pagination:**
- **Stable** — not affected by insertions/deletions
- **Fast** — index seek, no OFFSET scan
- **Consistent** — no duplicate/missing items

## Advanced Error Handling

### Custom Exception Handler

```python
from fastapi import Request, HTTPException
from fastapi.responses import JSONResponse
from datetime import datetime, timezone

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

@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """Unwrap HTTPException.detail so the wire format matches the documented schema.
    
    FastAPI's default handler wraps `detail` in `{"detail": ...}`, but our
    `responses={409: {"model": ErrorResponse}}` documents top-level fields.
    This handler returns the detail dict directly.
    """
    if isinstance(exc.detail, dict):
        body = dict(exc.detail)
        body.setdefault("details", None)
        body.setdefault("timestamp", datetime.now(timezone.utc).isoformat())
        body.setdefault("path", str(request.url))
        return JSONResponse(status_code=exc.status_code, content=body)
    
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

def raise_validation_error(errors: list[ValidationErrorDetail], path: str):
    raise HTTPException(
        status_code=422,
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
        status_code=409,
        detail={
            "error": "Conflict",
            "message": message,
            "details": details,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "path": path,
        }
    )
```

## GraphQL DataLoader (N+1 Prevention)

```python
from aiodataloader import DataLoader

class UserLoader(DataLoader):
    """Batch load users by ID — prevents N+1 queries."""
    
    async def batch_load_fn(self, user_ids: list[str]) -> list:
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

def create_context():
    return {
        "loaders": {
            "user": UserLoader(),
            "orders_by_user": OrdersByUserLoader()
        }
    }
```

**Why DataLoader:**
- **Batches** multiple requests into single query
- **Caches** within request scope
- **Prevents** N+1 query problem

## Advanced Webhook Patterns

### Retry Logic with Exponential Backoff

```python
class WebhookDeliveryError(Exception):
    """Raised when a webhook could not be delivered after all retries."""

_RETRYABLE_STATUSES = {408, 425, 429, 500, 502, 503, 504}

async def send_webhook(url: str, payload: dict, secret: str, max_attempts: int = 3):
    """Send webhook with HMAC signature and retry logic.
    
    Design choice: on final failure LOG and RAISE WebhookDeliveryError —
    silently returning None loses events. The caller must handle it:
    dead-letter queue, alert, or scheduled re-delivery job.
    
    Retries use exponential backoff on retryable failures (timeouts,
    connection errors, 408/425/429/5xx). Permanent 4xx errors
    (401, 403, 404, 410, 422) are dead-lettered immediately.
    """
    body = json.dumps(payload).encode()
    signature = hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
    webhook_id = str(uuid.uuid4())  # Stable across retries for dedup
    
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
                        "X-Webhook-Event": payload.get("event"),
                        "X-Webhook-ID": webhook_id,
                    },
                )
                if resp.status_code < 300:
                    return
                if resp.status_code not in _RETRYABLE_STATUSES:
                    logger.error(
                        "webhook to %s got permanent HTTP %d — dead-lettering",
                        url, resp.status_code,
                    )
                    raise WebhookDeliveryError(
                        f"receiver returned permanent error HTTP {resp.status_code}"
                    )
                last_error = WebhookDeliveryError(f"HTTP {resp.status_code}")
            except httpx.TransportError as exc:
                last_error = exc
            
            logger.warning(
                "webhook attempt %d/%d to %s failed: %s",
                attempt + 1, max_attempts, url, last_error,
            )
            if attempt < max_attempts - 1:
                await asyncio.sleep(2 ** attempt)  # Exponential backoff
    
    raise WebhookDeliveryError(
        f"webhook to {url} failed after {max_attempts} attempts"
    ) from last_error
```

## Long-Running Operations (202 Accepted)

```python
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
    await store_export_status(export_id, "pending", 0.0)
    bg.add_task(run_export, export_id, req)
    return ExportStatus(id=export_id, status="pending", progress=0.0)

@app.get("/exports/{export_id}")
async def get_export_status(export_id: str):
    status = await load_export_status(export_id)
    if not status:
        raise HTTPException(404, "Export not found")
    return status

# Client polls:
# GET /exports/{id} → {"status": "processing", "progress": 0.5}
# GET /exports/{id} → {"status": "completed", "download_url": "/downloads/abc.xlsx"}
```

## Express.js Advanced Patterns

### Router with Zod Validation

```typescript
import { Router } from 'express';
import { z } from 'zod';
import { validate } from '../middleware/validate';

const router = Router();

const CreateUserSchema = z.object({
  email: z.email(), // Zod 4 top-level format check
  name: z.string().min(1).max(100),
});

const PaginationSchema = z.object({
  page: z.coerce.number().int().positive().default(1),
  limit: z.coerce.number().int().min(1).max(100).default(20),
  cursor: z.string().optional(),
});

router.get('/users', validate({ query: PaginationSchema }), async (req, res) => {
  const { limit, cursor } = req.query;
  const take = Number(limit) + 1;
  const users = await db.user.findMany({
    take,
    skip: cursor ? 1 : undefined,
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

### Error Handling Middleware

```typescript
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
  console.error('Unhandled error:', err);
  res.status(500).json({
    error: { code: 'INTERNAL_ERROR', message: 'An unexpected error occurred' },
  });
};
```

## Edge Cases

### HATEOAS (Hypermedia as the Engine of Application State)

Responses contain links to related resources — the client navigates the API without knowing the URL structure.

```json
{
  "id": 123,
  "name": "John",
  "_links": {
    "self": {"href": "/api/users/123"},
    "orders": {"href": "/api/users/123/orders"},
    "profile": {"href": "/api/users/123/profile"}
  }
}
```

### Content Negotiation

```python
@app.get("/api/users/{id}")
async def get_user(id: int, accept: str = Header("application/json")):
    user = await fetch_user(id)
    
    if "application/xml" in accept:
        return Response(content=to_xml(user), media_type="application/xml")
    return user  # JSON by default
```

### Rate Limiting Headers

```python
@app.middleware("http")
async def add_rate_limit_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-RateLimit-Limit"] = "100"
    response.headers["X-RateLimit-Remaining"] = "95"
    response.headers["X-RateLimit-Reset"] = "1640000000"
    return response
```

## Performance Considerations

### Response Filtering

```python
@app.get("/api/users/{id}")
async def get_user(id: int, fields: str = Query(None)):
    user = await fetch_user(id)
    
    if fields:
        field_list = [f.strip() for f in fields.split(",")]
        return {k: v for k, v in user.items() if k in field_list}
    return user
```

### Compression

```python
from fastapi.middleware.gzip import GZipMiddleware

app.add_middleware(GZipMiddleware, minimum_size=1000)
```

## Troubleshooting

| Issue | Cause | Solution |
|-------|-------|----------|
| N+1 queries | Loading relations one-by-one | Use DataLoaders (GraphQL) or eager loading (REST) |
| Cursor pagination breaks | Invalid cursor format | Validate and decode with error handling |
| Idempotency conflicts | Same key, different payload | Return 409 with clear error |
| Webhook failures | Receiver down | Retry with backoff, dead-letter queue |
| Versioning confusion | No deprecation headers | Add Sunset and Deprecation headers |

## Additional Resources

- **Core patterns:** See [`SKILL.md`](SKILL.md) for essential patterns
- **Code examples:** See [`examples.md`](examples.md) for complete working examples
