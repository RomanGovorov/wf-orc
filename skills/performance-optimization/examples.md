# Code Examples: Performance Optimization

> Working examples for [`SKILL.md`](SKILL.md).

## Example 1: Complete CPU Profiling Setup

```python
import cProfile
import pstats
import io

def profile_function(func, *args, **kwargs):
    """Profile a function and return (result, stats_string)."""
    profiler = cProfile.Profile()
    profiler.enable()
    result = func(*args, **kwargs)
    profiler.disable()

    stream = io.StringIO()
    stats = pstats.Stats(profiler, stream=stream)
    stats.sort_stats("cumulative")
    stats.print_stats(20)
    return result, stream.getvalue()

# Usage
result, profile_output = profile_function(expensive_function, data)
print(profile_output)
```

### FastAPI Profiling Middleware

```python
from fastapi import FastAPI, Request
import time
import logging

logger = logging.getLogger(__name__)

app = FastAPI()

@app.middleware("http")
async def perf_tracking(request: Request, call_next):
    start = time.perf_counter()
    response = await call_next(request)
    duration = time.perf_counter() - start

    if duration > 1.0:
        logger.warning(
            "Slow request: %s %s took %.2fs",
            request.method, request.url.path, duration
        )

    response.headers["X-Response-Time"] = f"{duration:.3f}s"
    return response
```

## Example 2: Complete Database Query Optimization

```python
from sqlalchemy import Select, text
from sqlalchemy.orm import selectinload

# EXPLAIN analysis
def analyze_query(session, stmt):
    """Get query execution plan (SELECT only)."""
    if not isinstance(stmt, Select):
        raise TypeError("Only SELECT statements can be safely explained")
    sql = str(stmt)
    result = session.execute(text(f"EXPLAIN {sql}"), stmt.compile().params)
    return "\n".join(str(row[0]) for row in result)

# N+1 prevention with selectinload
from sqlalchemy import select

# ❌ BAD: N+1 queries
users = session.execute(select(User)).scalars().all()
for user in users:
    print(user.orders)  # Each access triggers a separate query!

# ✅ GOOD: Eager loading
stmt = select(User).options(selectinload(User.orders))
users = session.execute(stmt).scalars().all()
for user in users:
    print(user.orders)  # Already loaded — no additional queries
```

## Example 3: Complete Caching Implementation

### Redis Cache-Aside Pattern

```python
import redis
import json
from typing import Any

redis_client = redis.Redis(host="localhost", port=6379, db=0)

class RedisCache:
    def __init__(self, redis_client, default_ttl=300):
        self.redis = redis_client
        self.default_ttl = default_ttl

    def get(self, key: str) -> Any:
        data = self.redis.get(key)
        if data:
            return json.loads(data)
        return None

    def set(self, key: str, value: Any, ttl: int | None = None):
        self.redis.setex(key, ttl or self.default_ttl, json.dumps(value))

    def invalidate(self, key: str):
        self.redis.delete(key)

# Usage
user_cache = RedisCache(redis_client, default_ttl=600)

def get_user(user_id: str):
    cached = user_cache.get(f"user:{user_id}")
    if cached:
        return cached
    user = db.get_user(user_id)
    user_cache.set(f"user:{user_id}", user)
    return user

def update_user(user_id: str, data: dict):
    db.update_user(user_id, data)
    user_cache.invalidate(f"user:{user_id}")
```

### TTLCache for Mutable Data

```python
from cachetools import TTLCache

# 1000 items max, 5 minute TTL
cache = TTLCache(maxsize=1000, ttl=300)

def get_user_cached(user_id: str):
    if user_id in cache:
        return cache[user_id]
    user = db.get_user(user_id)
    cache[user_id] = user
    return user
```

## Example 4: Complete Async Optimization

### Parallel Execution with asyncio.gather

```python
import asyncio

# ❌ BAD: Sequential — 300ms total
async def get_dashboard_slow():
    user = await get_user_data()      # 100ms
    orders = await get_orders()        # 150ms
    notifications = await get_notifs() # 50ms
    return {"user": user, "orders": orders, "notifications": notifications}

# ✅ GOOD: Parallel — 150ms total
async def get_dashboard():
    user, orders, notifications = await asyncio.gather(
        get_user_data(),
        get_orders(),
        get_notifications()
    )
    return {"user": user, "orders": orders, "notifications": notifications}
```

### Structured Concurrency with TaskGroup

```python
# ✅ PREFERRED for cancellation safety (Python 3.11+)
async def fetch_all():
    async with asyncio.TaskGroup() as tg:
        users_task = tg.create_task(fetch_users())
        orders_task = tg.create_task(fetch_orders())
        products_task = tg.create_task(fetch_products())
    # If any task fails, ALL tasks are cancelled automatically
    return users_task.result(), orders_task.result(), products_task.result()

# With concurrency limit
async def fetch_batch(urls: list[str], max_concurrent: int = 10):
    sem = asyncio.Semaphore(max_concurrent)

    async def limited(url: str):
        async with sem:
            return await http_client.get(url)

    async with asyncio.TaskGroup() as tg:
        tasks = [tg.create_task(limited(url)) for url in urls]
    return [t.result() for t in tasks]
```

### Running CPU-Bound Work in Executor

```python
from concurrent.futures import ProcessPoolExecutor

executor = ProcessPoolExecutor()

async def process_data():
    loop = asyncio.get_running_loop()
    result = await loop.run_in_executor(executor, heavy_computation)
    return result
```

## Example 5: Complete Batch Processing

```python
from sqlalchemy import insert

# ❌ BAD: One-by-one insertion
for item in large_dataset:
    db.add(Item(**item))
    db.commit()  # N commits!

# ✅ GOOD: Bulk operations with batching
BATCH_SIZE = 1000
for i in range(0, len(large_dataset), BATCH_SIZE):
    batch = large_dataset[i:i + BATCH_SIZE]
    db.execute(Item.__table__.insert(), batch)
    db.commit()

# ✅ BETTER: SQLAlchemy 2.0 bulk insert
session.execute(insert(Item), large_dataset)
session.commit()
```

## Example 6: Complete Memory Optimization

### Keyset Pagination

```python
from sqlalchemy import select

async def fetch_users_keyset(session: AsyncSession, batch_size: int = 1000):
    """Stream users in batches using keyset pagination."""
    last_id = 0
    while True:
        result = await session.execute(
            select(User)
            .where(User.id > last_id)
            .order_by(User.id)
            .limit(batch_size)
        )
        batch = result.scalars().all()
        if not batch:
            break
        for user in batch:
            yield user
        last_id = batch[-1].id

# Streaming response
from fastapi.responses import StreamingResponse

async def user_iterator(session: AsyncSession):
    async for user in fetch_users_keyset(session):
        yield json.dumps(user.to_dict()) + "\n"

@app.get("/api/users/export")
async def export_users(session: AsyncSession = Depends(get_db_read)):
    return StreamingResponse(
        user_iterator(session),
        media_type="application/x-ndjson"
    )
```

## Example 7: Complete API Response Optimization

```python
from fastapi.middleware.gzip import GZipMiddleware
import hashlib
import json

app.add_middleware(GZipMiddleware, minimum_size=1000)

@app.get("/api/users/{user_id}")
async def get_user(user_id: str, request: Request, fields: str | None = None):
    user = await fetch_user(user_id)

    # Field selection
    if fields:
        requested = fields.split(",")
        user = {k: v for k, v in user.items() if k in requested}

    # ETag generation (RFC 9110: quoted string)
    etag = f'"{hashlib.md5(json.dumps(user).encode()).hexdigest()}"'

    if_none_match = request.headers.get("if-none-match")
    if if_none_match == etag:
        return Response(status_code=304)

    response = JSONResponse(user)
    response.headers["ETag"] = etag
    return response
```

## Example 8: Node.js Performance Patterns

### Redis Caching with ioredis

```typescript
import Redis from 'ioredis';

const redis = new Redis(process.env.REDIS_URL, {
  maxRetriesPerRequest: 3,
  lazyConnect: true,
});

async function getCached<T>(key: string, ttl: number, fn: () => Promise<T>): Promise<T> {
  const cached = await redis.get(key);
  if (cached) return JSON.parse(cached) as T;

  const result = await fn();
  await redis.setex(key, ttl, JSON.stringify(result));
  return result;
}

// Usage
const user = await getCached(`user:${id}`, 300, () => db.user.findById(id));
```

## Example 9: Database Read Replicas

```python
from fastapi import Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

primary_engine = create_async_engine(
    "postgresql+asyncpg://primary-host/db", pool_size=20
)
replica_engine = create_async_engine(
    "postgresql+asyncpg://replica-host/db", pool_size=30, pool_pre_ping=True
)

PrimarySession = async_sessionmaker(primary_engine, expire_on_commit=False)
ReplicaSession = async_sessionmaker(replica_engine, expire_on_commit=False)

async def get_db_write():
    async with PrimarySession() as session:
        yield session

async def get_db_read():
    async with ReplicaSession() as session:
        yield session

@app.get("/users")
async def list_users(db: AsyncSession = Depends(get_db_read)):
    result = await db.execute(select(User))
    return result.scalars().all()

@app.post("/users")
async def create_user(data: UserCreate, db: AsyncSession = Depends(get_db_write)):
    user = User(**data.model_dump())
    db.add(user)
    await db.commit()
    return user
```

---

## Additional Resources

- **Core patterns:** See [`SKILL.md`](SKILL.md) for essential patterns
- **Advanced techniques:** See [`advanced.md`](advanced.md) for deep dives and edge cases
