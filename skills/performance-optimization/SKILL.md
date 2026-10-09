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
# pyinstrument — readable output
# pip install pyinstrument
from pyinstrument import Profiler

profiler = Profiler()
profiler.start()
result = process_data()
profiler.stop()
print(profiler.output_text(unicode=True, color=True))

# FastAPI middleware for profiling
@app.middleware("http")
async def perf_tracking(request: Request, call_next):
    start = time.perf_counter()
    response = await call_next(request)
    duration = time.perf_counter() - start
    if duration > 1.0:
        logger.warning("Slow request: %s %s took %.2fs", request.method, request.url.path, duration)
    response.headers["X-Response-Time"] = f"{duration:.3f}s"
    return response
```

### Pattern 2: Database Query Optimization

```python
# SQLAlchemy — EXPLAIN for query plan analysis (SELECT only, bind params preserved)
#
# ⚠️ NEVER use EXPLAIN ANALYZE on UPDATE/DELETE: ANALYZE actually EXECUTES the
#    statement — on a write it mutates production data. Plain EXPLAIN only plans.
from sqlalchemy import Select, text

def analyze_query(session, stmt):
    """Get query execution plan for optimization (SELECT statements only)."""
    if not isinstance(stmt, Select):
        raise TypeError("Only SELECT statements can be safely explained")
    sql = str(stmt)
    result = session.execute(text(f"EXPLAIN {sql}"), stmt.compile().params)
    return "\n".join(str(row[0]) for row in result)
```

> **See also**: `database-patterns` — Connection pooling, N+1 prevention, indexing strategies, CQRS pattern.

### Pattern 3: Caching Strategies

```python
# LRU Cache — ONLY for PURE functions (no I/O, no DB!)
# ⚠️ @lru_cache never invalidates. For mutable data use TTLCache or Redis.
from functools import lru_cache

@lru_cache(maxsize=256)
def compute_discount(quantity: int, unit_price: float, tier: str) -> float:
    """Pure computation — safe for lru_cache."""
    base = quantity * unit_price
    rates = {"gold": 0.20, "silver": 0.10, "bronze": 0.05}
    return base * (1 - rates.get(tier, 0))

# TTL Cache — expiring cache for mutable data
# pip install cachetools
from cachetools import TTLCache
cache = TTLCache(maxsize=1000, ttl=300)  # 1000 items, 5 min TTL

def get_user_cached(user_id: str):
    if user_id in cache:
        return cache[user_id]
    user = db.get_user(user_id)
    cache[user_id] = user
    return user
```

**Cache Strategy Matrix:**

| Strategy | When to Use | Pros | Cons |
|---|---|---|---|
| Cache-Aside (Lazy) | Read-heavy workloads | Simplicity, efficiency | First cache hit slow |
| Write-Through | Data consistency | Always fresh sync | Slower writes |
| Write-Behind | High write volume | Faster writes | Risk of data loss |
| Refresh-Ahead | Predictable access | No cache miss latency | Wasted refreshes |

### Pattern 4: Async Optimization

```python
# ❌ BAD: Sequential async — no parallelism
async def get_dashboard():
    user = await get_user_data()      # 100ms
    orders = await get_orders()        # 150ms — waits!
    notifications = await get_notifs() # 50ms — waits!
    return {"user": user, "orders": orders, "notifications": notifications}
    # Total: 300ms

# ✅ GOOD: Parallel async with asyncio.gather
async def get_dashboard():
    user, orders, notifications = await asyncio.gather(
        get_user_data(), get_orders(), get_notifications()
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
```

### Pattern 5: Batch Processing

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

# ✅ GOOD: SQLAlchemy 2.0 bulk insert
from sqlalchemy import insert
session.execute(insert(Item), large_dataset)
session.commit()
```

## Key Pitfalls

| Mistake | Why It's Bad | Fix |
|---|---|---|
| Premature optimization | Makes code complex without knowing bottleneck | Profile first |
| N+1 queries (not noticed) | 1000 queries instead of 2 | selectinload, DataLoaders |
| Cache stampede | 100 simultaneous requests on cache miss | Lock or stale-while-revalidate |
| No connection pool limit | DB overload on traffic spike | pool_size + max_overflow |
| `time.sleep()` in async | Blocks entire event loop | asyncio.sleep() |
| Blocking I/O in async function | Serial instead of parallel | httpx, asyncpg, aiosqlite |
| Cache invalidation missing | Stale data | Invalidate on write, TTL |
| Fetch all then paginate | OOM | Keyset/cursor batching — never deep LIMIT/OFFSET |
| Over-indexing | Slows down inserts/updates | Only needed indexes |
| Missing query plans | Unoptimized query | EXPLAIN (never EXPLAIN ANALYZE on writes) |

## Best Practices

1. **Profile first, optimize second** — data, not guesses
2. **N+1 queries — fix first** — this is the #1 bottleneck
3. **Connection pooling** — configure pool_size based on load test
4. **Cache read-heavy, rarely-changing data** — user roles, config, catalog
5. **Batch insert/update** — reduce round trips
6. **Streaming for large datasets** — constant memory footprint
7. **asyncio.TaskGroup** (Python 3.11+) for independent I/O — structured concurrency; **asyncio.gather()** for simple fan-out without cancellation safety
8. **Index only frequently-queried columns** — indexes slow down writes
9. **Set realistic SLOs** — p95 < 500ms, p99 < 1s
10. **Load test before production** — identify bottlenecks under load

## Additional Resources

- **Advanced patterns:** See [`advanced.md`](advanced.md) for memory optimization, API response optimization, structured concurrency, CDN/edge caching, database read replicas, and cache stampede prevention
- **Code examples:** See [`examples.md`](examples.md) for complete working examples and templates

## See also

> **See also**: `python-professional` — SQLAlchemy 2.0 model patterns, session management, Alembic migrations.
> **See also**: `api-design-principles` — cursor-based pagination, HATEOAS.
> **See also**: `database-patterns` — Connection pooling, N+1 prevention, indexing strategies, CQRS pattern.

## Context7 Integration

When Context7 MCP tools are available in your session, use them to fetch up-to-date library documentation instead of relying on memory. Tool names vary by installation (e.g. `mcp__context7__resolve-library-id` / `mcp__context7__query-docs`, or plugin-prefixed variants such as `mcp__plugin_context7_context7__*`) — check the available-tools listing for the exact names. Always resolve the library ID first; the IDs in the table below are examples and may change.

| Library | Context7 ID | When to Query |
|---------|-------------|---------------|
| SQLAlchemy | `/websites/sqlalchemy_en_20` | Query optimization, eager loading |
| Redis | (query "Redis") | Caching, pub/sub |
| Prometheus | (query "Prometheus Python") | Metrics collection |
| pyinstrument | (query "pyinstrument") | Profiling |
| memray | (query "memray") | Memory profiling |
