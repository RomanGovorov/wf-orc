# Advanced Patterns: Performance Optimization

> This file extends [`SKILL.md`](SKILL.md) with advanced patterns and edge cases.

## Memory Optimization

### Keyset (Seek) Pagination

```python
# ❌ BAD: Load all into memory
async def export_all(session: AsyncSession):
    all_users = (await session.execute(select(User))).scalars().all()  # 1M users → OOM
    for user in all_users:
        process(user)

# ✅ GOOD: Keyset pagination — constant memory, async end-to-end.
# NEVER use LIMIT/OFFSET for deep pages: skipping N rows costs O(N) per page
# (O(N²) overall) and rows shift under concurrent writes.
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
```

### Streaming Response

```python
# ✅ GOOD: Streaming response for large datasets
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

### Memory Profiling

```python
# tracemalloc — built-in memory tracking
import tracemalloc
tracemalloc.start()
# ... code to profile ...
snapshot = tracemalloc.take_snapshot()
top_stats = snapshot.statistics("lineno")
for stat in top_stats[:10]:
    print(stat)

# memray — modern memory profiler (pip install memray)
import memray
with memray.Tracker("memory_profile.bin"):
    # ... code to profile ...
    pass
# Analyze:
# $ memray summary memory_profile.bin
# $ memray flamegraph memory_profile.bin
```

## API Response Optimization

### Compression + Field Selection + ETag

```python
# Response compression
from fastapi.middleware.gzip import GZipMiddleware
app.add_middleware(GZipMiddleware, minimum_size=1000)  # Compress >1KB

# Field selection + ETag — ONE handler per path
import hashlib
import json

@app.get("/api/users/{user_id}")
async def get_user(user_id: str, request: Request, fields: str | None = None):
    user = await fetch_user(user_id)
    if fields:
        requested = fields.split(",")
        user = {k: v for k, v in user.items() if k in requested}

    # RFC 9110: entity-tag is a QUOTED string
    etag = f'"{hashlib.md5(json.dumps(user).encode()).hexdigest()}"'
    if_none_match = request.headers.get("if-none-match")
    if if_none_match == etag:
        return Response(status_code=304)
    response = JSONResponse(user)
    response.headers["ETag"] = etag
    return response
```

## Structured Concurrency (Python 3.11+ TaskGroup)

```python
# asyncio.gather — acceptable for SIMPLE fan-out, but not cancellation-safe:
# when one coroutine fails, siblings keep running (tasks leak)
async def fetch_all_gather():
    results = await asyncio.gather(
        fetch_users(), fetch_orders(), fetch_products(),
        return_exceptions=True  # hides errors — inspect each result!
    )

# ✅ PREFERRED — TaskGroup (structured concurrency, Python 3.11+):
async def fetch_all():
    async with asyncio.TaskGroup() as tg:
        users_task = tg.create_task(fetch_users())
        orders_task = tg.create_task(fetch_orders())
        products_task = tg.create_task(fetch_products())
    # If any task fails, ALL tasks are cancelled
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

## CPU-Bound Work in Async

```python
# ❌ BAD: CPU-bound in async — blocks event loop
async def process_data():
    result = heavy_computation()
    return result

# ✅ GOOD: Run in executor
from concurrent.futures import ProcessPoolExecutor
executor = ProcessPoolExecutor()

async def process_data():
    loop = asyncio.get_running_loop()
    result = await loop.run_in_executor(executor, heavy_computation)
    return result
```

## Profiling Tools Comparison

| Tool | Type | Overhead | Best For | Output |
|------|------|----------|----------|--------|
| `cProfile` | CPU | Low | Function call counts | .prof file (SnakeViz) |
| `pyinstrument` | CPU (wall-clock) | <1% | High-level bottlenecks | HTML flame chart |
| `memray` | Memory | Medium | Memory leaks, allocations | HTML flame graph |
| `py-spy` | CPU (sampling) | <1% | Production profiling | Speedscope JSON |
| `austin` | CPU + RSS | Low | Lightweight sampling | Flame charts |
| `yappi` | CPU + threads | Low | Async/multithreaded | Callgrind format |

```bash
# Quick profiling commands
pyinstrument -m pytest tests/test_slow.py     # What's slow?
memray run --trace-python-allocators app.py   # Where's memory going?
py-spy top --pid $(pgrep python)              # Live CPU monitoring
py-spy record -o profile.svg --pid $(pgrep python)  # Record flame graph
```

## CDN and Edge Caching

```python
from fastapi import FastAPI, Header, Response

app = FastAPI()

@app.get("/api/products/{id}")
async def get_product(id: int, response: Response):
    product = await get_product_from_db(id)
    # Cache at CDN for 5 min, revalidate in background
    response.headers["Cache-Control"] = "public, max-age=300, stale-while-revalidate=60"
    response.headers["ETag"] = f'"{product.version}"'
    return product

@app.get("/api/users/me")
async def get_current_user(response: Response):
    # Never cache user-specific data
    response.headers["Cache-Control"] = "private, no-store"
    return await get_user()

# Vary header for content negotiation
@app.get("/api/data")
async def get_data(accept: str = Header("text/html"), response: Response | None = None):
    response.headers["Vary"] = "Accept, Accept-Encoding"
    if "application/json" in accept:
        return data_json()
    return data_html()
```

## Database Read Replicas

```python
from fastapi import Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

# Primary (read-write) — async engine + asyncio driver (asyncpg).
# NEVER mix a sync sessionmaker with `async def` handlers.
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

## Node.js Performance Patterns

### Profiling with clinic.js

```bash
clinic doctor -- node server.js
clinic flame -- node server.js
clinic bubbleprof -- node server.js     # async activity
clinic heapprofiler -- node server.js
```

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

const user = await getCached(`user:${id}`, 300, () => db.user.findById(id));
```

## Cache Stampede Prevention

When a cache entry expires under high concurrency, multiple requests simultaneously try to recompute — causing a thundering herd.

### Lock-Based Approach

```python
import asyncio
from functools import wraps

def cache_with_lock(ttl: int):
    """Prevent cache stampede with async lock."""
    _lock = asyncio.Lock()
    _cache = {}

    def decorator(func):
        @wraps(func)
        async def wrapper(*args):
            key = str(args)
            if key in _cache and not _cache[key]['expired']:
                return _cache[key]['value']
            async with _lock:
                if key in _cache and not _cache[key]['expired']:
                    return _cache[key]['value']
                value = await func(*args)
                _cache[key] = {'value': value, 'expired': False}
                asyncio.get_running_loop().call_later(
                    ttl, lambda: _cache[key].__setitem__('expired', True)
                )
                return value
        return wrapper
    return decorator

@cache_with_lock(ttl=300)
async def get_user_profile(user_id: str):
    return await db.fetch_user_profile(user_id)
```

### Stale-While-Revalidate

```python
import time

class StaleWhileRevalidateCache:
    """Serve stale data immediately while refreshing in background."""
    def __init__(self, ttl: int = 300, stale_ttl: int = 60):
        self._cache: dict = {}
        self._ttl = ttl
        self._stale_ttl = stale_ttl

    async def get(self, key: str, fetch_fn):
        entry = self._cache.get(key)
        now = time.monotonic()
        if entry:
            age = now - entry['created_at']
            if age < self._ttl:
                return entry['value']  # Fresh
            if age < self._ttl + self._stale_ttl:
                asyncio.create_task(self._revalidate(key, fetch_fn))
                return entry['value']  # Stale but servable
        return await self._revalidate(key, fetch_fn)

    async def _revalidate(self, key: str, fetch_fn):
        value = await fetch_fn()
        self._cache[key] = {'value': value, 'created_at': time.monotonic()}
        return value
```

---

## Additional Resources

- **Core patterns:** See [`SKILL.md`](SKILL.md) for essential patterns
- **Code examples:** See [`examples.md`](examples.md) for complete working examples
