---
name: performance-optimization
description: Profiling patterns, caching, database optimization, memory management, and async code. Use when analyzing bottlenecks, optimizing slow queries, or configuring scalability.
priority: 5
paths:
  - "**/performance*"
  - "**/profiling*"
  - "**/cache*"
  - "**/benchmark*"
  - "**/load-test*"
  - "**/optimize*"
  - "**/slow*"
  - "**/bottleneck*"
---

# Performance Optimization Patterns

Bottleneck detection and resolution patterns — profiling, caching, database optimization, memory management, async patterns.

## When to Use This Skill

- When identifying slow endpoints (>SLO)
- When profiling CPU, memory, I/O bottlenecks
- When optimizing N+1 queries
- When configuring caching strategies
- When analyzing memory leaks
- When working with large data volumes (batch processing)
- When optimizing async/await code

## Core Concepts

### 1. Measure Before Optimizing

- **Golden Rule**: Never optimize without profiling — measurements will reveal the real bottleneck
- **80/20 Rule**: 20% of code consumes 80% of time
- **SLO-driven**: Optimization must have a target SLO (e.g., p99 < 200ms)

### 2. Bottleneck Categories

| Category | Symptoms | Tools | Typical Fix |
|---|---|---|---|
| CPU-bound | 100% CPU, slow computation | cProfile, py-spy | Algorithm, caching, multiprocessing |
| I/O-bound | Wait time > CPU time | asyncio debug, strace | Async, connection pooling, batching |
| DB-bound | Slow queries, high latencies | EXPLAIN ANALYZE, query logs | Indexes, query rewrite, N+1 fix |
| Memory | Growing RSS, OOM | tracemalloc, memray | Generators, streaming, cache eviction |
| Network | High latency between services | tcpdump, jaeger | Compression, connection reuse, CDN |

### 3. Latency Budget

| Operation | Expected Latency |
|---|---|
| L1 cache reference | 0.5 ns |
| L2 cache reference | 7 ns |
| RAM access | 100 ns |
| SSD read | 150 μs |
| Database query (indexed) | 1 ms |
| Python function call | 0.5 μs |
| Network round trip (same DC) | 0.5 ms |
| Network round trip (cross-region) | 150 ms |

## Patterns

### Pattern 1: CPU Profiling (cProfile + pyinstrument)

```python
# cProfile — standard library
import cProfile
import pstats

def profile_endpoint():
    profiler = cProfile.Profile()
    profiler.enable()

    # Code to profile
    result = expensive_function()

    profiler.disable()
    stats = pstats.Stats(profiler).sort_stats("cumulative")
    stats.print_stats(20)  # Top 20 functions
    return result

# pyinstrument — more readable output
# pip install pyinstrument
from pyinstrument import Profiler

profiler = Profiler()
profiler.start()

# Execute operation
result = process_data()

profiler.stop()
print(profiler.output_text(unicode=True, color=True))

# FastAPI middleware for profiling
from fastapi import Request
import time

@app.middleware("http")
async def perf_tracking(request: Request, call_next):
    start = time.perf_counter()  # More precise than time.time() for durations
    response = await call_next(request)
    duration = time.perf_counter() - start

    # Slow request logging
    if duration > 1.0:
        logger.warning(
            "Slow request: %s %s took %.2fs",
            request.method, request.url.path, duration
        )

    response.headers["X-Response-Time"] = f"{duration:.3f}s"
    return response
```

### Pattern 2: Database Query Optimization

```python
# SQLAlchemy — EXPLAIN ANALYZE for query plan analysis
from sqlalchemy import text

def analyze_query(session, stmt):
    """Get query execution plan for optimization."""
    query_text = str(stmt.compile(compile_kwargs={"literal_binds": True}))
    result = session.execute(text(f"EXPLAIN ANALYZE {query_text}"))
    return "\n".join(row[0] for row in result)
```

> **See also**: `database-patterns` — Connection pooling, N+1 prevention, indexing strategies, CQRS pattern.

### Pattern 3: Caching Strategies

```python
# LRU Cache — in-memory for PURE functions (no I/O, no DB!)
# ⚠️ WARNING: @lru_cache never invalidates. Use ONLY for:
#   - Pure computations (math, parsing, deterministic transforms)
#   - Static/reference data that never changes (country codes, MIME types)
# For mutable data (DB queries, API calls), use TTLCache or Redis with invalidation.
from functools import lru_cache

@lru_cache(maxsize=256)
def compute_discount(quantity: int, unit_price: float, tier: str) -> float:
    """Pure computation — safe for lru_cache (no I/O, deterministic)."""
    base = quantity * unit_price
    rates = {"gold": 0.20, "silver": 0.10, "bronze": 0.05}
    return base * (1 - rates.get(tier, 0))

# For mutable/reference data use TTLCache (see below) instead:
# from cachetools import TTLCache
# role_cache = TTLCache(maxsize=256, ttl=300)  # expires after 5 min

# TTL Cache — expiring cache for data with TTL
# pip install cachetools
from cachetools import TTLCache

# 1000 items max, 5 minute TTL
cache = TTLCache(maxsize=1000, ttl=300)

def get_user_cached(user_id: str):
    if user_id in cache:
        return cache[user_id]

    user = db.get_user(user_id)
    cache[user_id] = user
    return user

# Redis cache — distributed cache for web servers
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

    def set(self, key: str, value: Any, ttl: int = None):
        self.redis.setex(
            key,
            ttl or self.default_ttl,
            json.dumps(value)
        )

    def invalidate(self, key: str):
        self.redis.delete(key)

# Cache-Aside Pattern
user_cache = RedisCache(redis_client, default_ttl=600)

def get_user(user_id: str):
    # 1. Try cache
    cached = user_cache.get(f"user:{user_id}")
    if cached:
        return cached

    # 2. Cache miss — load from DB
    user = db.get_user(user_id)

    # 3. Store in cache
    user_cache.set(f"user:{user_id}", user)

    return user

def update_user(user_id: str, data: dict):
    db.update_user(user_id, data)
    user_cache.invalidate(f"user:{user_id}")  # Prevent stale data
```

**Cache Strategy Matrix:**

| Strategy | When to Use | Pros | Cons |
|---|---|---|---|
| Cache-Aside (Lazy) | Read-heavy workloads | Simplicity, efficiency | First cache hit slow |
| Write-Through | Data consistency | Always fresh sync | Slower writes |
| Write-Behind | High write volume | Faster writes | Risk of data loss |
| Refresh-Ahead | Predictable access | No cache miss latency | Wasted refreshes |

> **See also**: `database-patterns` — Connection pooling, N+1 prevention, indexing strategies, CQRS pattern.

### Pattern 4: Async Optimization

```python
# ❌ BAD: Sequential async — no parallelism
async def get_dashboard():
    user = await get_user_data()      # 100ms
    orders = await get_orders()        # 150ms — waits!
    notifications = await get_notifs() # 50ms — waits!
    return {"user": user, "orders": orders, "notifications": notifications}
    # Total: 300ms

# ✅ GOOD: Parallel async — gather
async def get_dashboard():
    user, orders, notifications = await asyncio.gather(
        get_user_data(),
        get_orders(),
        get_notifications()
    )
    return {"user": user, "orders": orders, "notifications": notifications}
    # Total: 150ms (longest operation)

# ❌ BAD: Blocking I/O in async
async def fetch_url(url):
    import requests  # BLOCKS the event loop!
    return requests.get(url)

# ✅ GOOD: Async HTTP client
import httpx

async with httpx.AsyncClient() as client:
    response = await client.get(url)

# ❌ BAD: CPU-bound in async
async def process_data():
    # Heavy computation — blocks event loop
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

### Pattern 6: Batch Processing

```python
# ❌ BAD: One-by-one insertion
for item in large_dataset:
    db.add(Item(**item))
    db.commit()  # N commits!

# ✅ GOOD: Bulk operations
BATCH_SIZE = 1000
for i in range(0, len(large_dataset), BATCH_SIZE):
    batch = large_dataset[i:i + BATCH_SIZE]
    db.execute(Item.__table__.insert(), batch)
    db.commit()

# ✅ GOOD: SQLAlchemy 2.0 bulk insert via insert() construct
from sqlalchemy import insert
session.execute(insert(Item), large_dataset)
session.commit()
```

### Pattern 7: Memory Optimization

```python
# ❌ BAD: Load all into memory
all_users = session.execute(select(User)).scalars().all()  # 1 million users → OOM
for user in all_users:
    process(user)

# ✅ GOOD: Yield results — generator
def fetch_users_batched(session, batch_size=1000):
    """Stream results in batches — constant memory."""
    offset = 0
    while True:
        batch = (
            session.execute(
                select(User)
                .order_by(User.id)
                .limit(batch_size)
                .offset(offset)
            )
            .scalars()
            .all()
        )
        if not batch:
            break
        yield from batch
        offset += batch_size

# ✅ GOOD: Streaming response for large datasets
from fastapi.responses import StreamingResponse

async def user_iterator():
    for user in fetch_users_batched(session):
        yield json.dumps(user.to_dict()) + "\n"

@app.get("/api/users/export")
async def export_users():
    return StreamingResponse(
        user_iterator(),
        media_type="application/x-ndjson"
    )
```

**Memory Monitoring:**

```python
# tracemalloc — built-in memory tracking
import tracemalloc

tracemalloc.start()

# ... code to profile ...

snapshot = tracemalloc.take_snapshot()
top_stats = snapshot.statistics("lineno")
print("[Top 10 memory allocations]")
for stat in top_stats[:10]:
    print(stat)

# memray — memory profiler (pip install memray)
# Modern replacement for pympler (unmaintained since 2022)
import memray

with memray.Tracker("memory_profile.bin"):
    # ... code to profile ...
    pass

# Analyze results:
# $ memray summary memory_profile.bin     — top allocations
# $ memray flamegraph memory_profile.bin  — visual flame graph
# $ memray table memory_profile.bin       — allocation table
```

### Pattern 8: API Response Optimization

```python
# Response compression
from fastapi.middleware.gzip import GZipMiddleware

app.add_middleware(GZipMiddleware, minimum_size=1000)  # Compress >1KB

# Field selection — GraphQL style for REST
@app.get("/api/users/{user_id}")
async def get_user(user_id: str, fields: str | None = None):
    user = await fetch_user(user_id)

    if fields:
        requested = fields.split(",")
        return {k: v for k, v in user.items() if k in requested}

    return user

# ETag / conditional requests
from fastapi import Request
import hashlib

@app.get("/api/users/{user_id}")
async def get_user(user_id: str, request: Request):
    user = await fetch_user(user_id)
    etag = hashlib.md5(json.dumps(user).encode()).hexdigest()

    if_none_match = request.headers.get("if-none-match")
    if if_none_match == etag:
        return Response(status_code=304)  # Not Modified — use cache

    response = JSONResponse(user)
    response.headers["ETag"] = etag
    return response
```

### Node.js Performance Patterns

#### Profiling with clinic.js
```bash
# CPU profiling
clinic doctor -- node server.js
clinic flame -- node server.js

# Bubbleprof for async activity
clinic bubbleprof -- node server.js

# Heap profiling
clinic heapprofiler -- node server.js
```

#### Redis Caching with ioredis
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

### Structured Concurrency (Python 3.11+ TaskGroup)
```python
import asyncio

# ❌ Old — asyncio.gather (tasks leak on cancellation)
async def fetch_all_old():
    results = await asyncio.gather(
        fetch_users(), fetch_orders(), fetch_products(),
        return_exceptions=True  # hides errors
    )

# ✅ New — TaskGroup (structured concurrency)
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

### Profiling Tools Comparison

| Tool | Type | Overhead | Best For | Output |
|------|------|----------|----------|--------|
| `cProfile` | CPU | Low | Function call counts | .prof file (SnakeViz) |
| `pyinstrument` | CPU (wall-clock) | <1% | High-level bottlenecks | HTML flame chart |
| `memray` | Memory | Medium | Memory leaks, allocations | HTML flame graph |
| `py-spy` | CPU (sampling) | <1% | Production profiling | Speedscope JSON |
| `Austin` | CPU + Memory | Low | Lightweight sampling | Flame charts |
| `yappi` | CPU + threads | Low | Async/multithreaded | Callgrind format |

```bash
# Quick profiling commands
pyinstrument -m pytest tests/test_slow.py     # What's slow?
memray run --trace-python-allocators app.py   # Where's memory going?
py-spy top --pid $(pgrep python)              # Live CPU monitoring
py-spy record -o profile.svg --pid $(pgrep python)  # Record flame graph
```

### CDN and Edge Caching
```python
# FastAPI — set cache headers for CDN
from fastapi import FastAPI, Response

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

# Cloudflare/CloudFront cache key includes query params
# Vary header for content negotiation
@app.get("/api/data")
async def get_data(accept: str = Header("text/html"), response: Response = None):
    response.headers["Vary"] = "Accept, Accept-Encoding"
    if "application/json" in accept:
        return data_json()
    return data_html()
```

### Database Read Replicas
```python
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Primary (read-write)
primary_engine = create_engine("postgresql://primary-host/db", pool_size=20)
# Replica (read-only)
replica_engine = create_engine("postgresql://replica-host/db", pool_size=30, pool_pre_ping=True)

PrimarySession = sessionmaker(bind=primary_engine)
ReplicaSession = sessionmaker(bind=replica_engine)

# Route writes to primary, reads to replica
class DatabaseRouter:
    def get_write_session(self):
        return PrimarySession()

    def get_read_session(self):
        return ReplicaSession()

# FastAPI dependencies
def get_db_write():
    with PrimarySession() as session:
        yield session

def get_db_read():
    with ReplicaSession() as session:
        yield session

@app.get("/users")
async def list_users(db=Depends(get_db_read)):  # reads from replica
    return db.execute(select(User)).scalars().all()

@app.post("/users")
async def create_user(data: UserCreate, db=Depends(get_db_write)):  # writes to primary
    user = User(**data.model_dump())
    db.add(user)
    await db.commit()
    return user
```

> **See also**: `python-professional` — SQLAlchemy 2.0 model patterns, session management, Alembic migrations. `api-design-principles` — cursor-based pagination, HATEOAS.

## Best Practices

1. **Profile first, optimize second** — data, not guesses
2. **N+1 queries — fix first** — this is the #1 bottleneck
3. **Connection pooling** — configure pool_size based on load test
4. **Cache read-heavy, rarely-changing data** — user roles, config, catalog
5. **Batch insert/update** — reduce round trips
6. **Streaming for large datasets** — constant memory footprint
7. **async.gather()** for independent I/O operations
8. **Index only frequently-queried columns** — indexes slow down writes
9. **Set realistic SLOs** — p95 < 500ms, p99 < 1s
10. **Load test before production** — identify bottlenecks under load

## Common Pitfalls

| Mistake | Why It's Bad | Fix |
|---|---|---|
| Premature optimization | Makes code complex without knowing bottleneck | Profile first |
| N+1 queries (not noticed) | 1000 queries instead of 2 | selectinload, DataLoaders |
| Cache stampede | 100 simultaneous requests on cache miss | Lock or stale-while-revalidate (see pattern below) |
| No connection pool limit | DB overload on traffic spike | pool_size + max_overflow |
| `time.sleep()` in async | Blocks entire event loop | asyncio.sleep() |
| Blocking I/O in async function | Serial instead of parallel | httpx, asyncpg, aiosqlite |
| Cache invalidation missing | Stale data | Invalidate on write, TTL |
| Fetch all then paginate | OOM | LIMIT/OFFSET, cursor |
| Over-indexing | Slows down inserts/updates | Only needed indexes |
| Missing query plans | Unoptimized query | EXPLAIN ANALYZE |

### Cache Stampede Prevention Pattern

When a cache entry expires under high concurrency, multiple requests simultaneously try to recompute the value — causing a thundering herd. Use a lock to ensure only one request rebuilds the cache while others wait or receive stale data.

```python
import asyncio
from functools import wraps

def cache_with_lock(ttl: int):
    """Prevent cache stampede with async lock.

    Only one caller recomputes the value on cache miss/expiry.
    All other concurrent callers wait on the lock and then read
    the freshly cached result (double-checked locking).
    """
    _lock = asyncio.Lock()
    _cache = {}

    def decorator(func):
        @wraps(func)
        async def wrapper(*args):
            key = str(args)
            # Fast path — return cached value if not expired
            if key in _cache and not _cache[key]['expired']:
                return _cache[key]['value']

            # Slow path — acquire lock, double-check, then compute
            async with _lock:
                if key in _cache and not _cache[key]['expired']:
                    return _cache[key]['value']
                value = await func(*args)
                _cache[key] = {'value': value, 'expired': False}
                # Schedule expiration without blocking
                asyncio.get_running_loop().call_later(
                    ttl, lambda: _cache[key].__setitem__('expired', True)
                )
                return value
        return wrapper
    return decorator


# Usage
@cache_with_lock(ttl=300)  # 5-minute TTL
async def get_user_profile(user_id: str):
    """Expensive DB query — protected from stampede."""
    return await db.fetch_user_profile(user_id)


# Alternative: stale-while-revalidate (serve stale, refresh in background)
import time

class StaleWhileRevalidateCache:
    """Serve stale data immediately while refreshing in the background.

    - ttl: how long the value is considered fresh
    - stale_ttl: how long stale data can be served while revalidating
    """

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
                # Stale but servable — revalidate in background
                # NOTE: fire-and-forget — exceptions in _revalidate are silently lost.
                # For production, wrap in a try/except or use a background worker.
                asyncio.create_task(self._revalidate(key, fetch_fn))
                return entry['value']

        # Cache miss or too stale — fetch synchronously
        return await self._revalidate(key, fetch_fn)

    async def _revalidate(self, key: str, fetch_fn):
        value = await fetch_fn()
        self._cache[key] = {'value': value, 'created_at': time.monotonic()}
        return value
```

## Context7 Integration

When working with performance patterns, verify against current documentation:

| Library | Context7 ID | When to Query |
|---------|-------------|---------------|
| SQLAlchemy | `/websites/sqlalchemy_en_20` | Query optimization, eager loading |
| Redis | (query "Redis") | Caching, pub/sub |
| Prometheus | (query "Prometheus Python") | Metrics collection |
| pyinstrument | (query "pyinstrument") | Profiling |
| memray | (query "memray") | Memory profiling |

Use `mcp__context7__resolve-library-id` then `mcp__context7__query-docs` to get current examples.
