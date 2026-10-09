---
name: database-patterns
description: Database design patterns — connection pooling, async sessions, Alembic migrations, indexing, N+1 prevention, transaction isolation, CQRS, repository pattern, soft delete, bulk operations. Use when designing schemas, writing queries, configuring pools, planning migrations.
priority: 10
paths:
  - "**/models*"
  - "**/migrations/**"
  - "**/alembic/**"
  - "**/queries*"
  - "**/db/**"
  - "**/database/**"
  - "**/schema*"
  - "**/repository*"
---

# Database Patterns

Complete guide to database design and optimization — normalization, indexing, migrations, connection pooling, transactions, CQRS, repository pattern, bulk operations.

## When to Use This Skill

- When designing database schemas (normalization, denormalization)
- When writing or optimizing SQL queries
- When configuring connection pools (SQLAlchemy, asyncpg)
- When planning or executing database migrations (Alembic)
- When choosing indexing strategies
- When implementing transaction isolation levels
- When designing CQRS or repository patterns
- When working with bulk insert/upsert operations
- When implementing soft delete logic
- When preventing N+1 query problems

## Core Concepts

### Normalization

- **1NF** — atomic values, no repeating groups
- **2NF** — 1NF + no partial dependencies (all non-key columns depend on the whole key)
- **3NF** — 2NF + no transitive dependencies (non-key columns don't depend on other non-key columns)
- **BCNF** — every determinant is a candidate key
- **Denormalization** — intentional redundancy for read performance; document the reason

### CAP Theorem

| Property | Description | Trade-off |
|----------|-------------|-----------|
| **Consistency** | Every read returns the most recent write | Higher latency |
| **Availability** | Every request gets a response | Possible stale reads |
| **Partition Tolerance** | System works despite network partitions | Mandatory in distributed systems |

- **CP** — etcd, ZooKeeper (consensus systems)
- **AP** — Cassandra, DynamoDB
- **CA** — single-node PostgreSQL/MySQL (no replication)

### ACID Properties

| Property | Description | SQLAlchemy Control |
|----------|-------------|-------------------|
| **Atomicity** | All-or-nothing transactions | `session.commit()` / `session.rollback()` |
| **Consistency** | Valid state transitions | Constraints, check constraints, triggers |
| **Isolation** | Concurrent transactions don't interfere | `isolation_level` parameter |
| **Durability** | Committed data survives crashes | WAL, fsync (DB-level) |

---

## Patterns

### 1. Connection Pooling

```python
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker

engine = create_async_engine(
    "postgresql+asyncpg://user:pass@localhost/mydb",
    pool_size=20,           # Persistent connections in pool
    max_overflow=10,        # Extra connections during spikes (total = 30)
    pool_timeout=30,        # Seconds to wait for available connection
    pool_recycle=1800,      # Recycle connections every 30 min
    pool_pre_ping=True,     # Test connection before use
    echo=False,             # Disable SQL logging in production
    connect_args={"server_settings": {"application_name": "myapp"}},
)

AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,  # Don't expire after commit — safe for API responses
)

from collections.abc import AsyncGenerator

async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
```

**Pool sizing formula:** `connections = ((cpu_cores * 2) + effective_spindle_count)` — SSD: spindle=1

### 2. Session Management

```python
# ✅ GOOD: expire_on_commit=False for API responses
AsyncSessionLocal = async_sessionmaker(
    engine, class_=AsyncSession, expire_on_commit=False,
)

# ✅ GOOD: Unit of Work pattern — explicit commit boundaries
class UnitOfWork:
    def __init__(self, session_factory: async_sessionmaker[AsyncSession]):
        self._session_factory = session_factory
        self._session: AsyncSession | None = None

    async def __aenter__(self) -> AsyncSession:
        self._session = self._session_factory()
        return self._session

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if exc_type is not None:
            await self._session.rollback()
        else:
            await self._session.commit()
        await self._session.close()
```

### 3. Alembic Migrations (Brief)

```python
# alembic/env.py — async-compatible configuration
import asyncio
from sqlalchemy.ext.asyncio import create_async_engine
from alembic import context

target_metadata = Base.metadata

async def run_async_migrations():
    connectable = create_async_engine(settings.DATABASE_URL)
    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)
    await connectable.dispose()

def run_migrations_online():
    asyncio.run(run_async_migrations())

if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
```

### 4. Indexing Strategies

```python
from sqlalchemy import Index, text

class Order(Base):
    __tablename__ = "orders"
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    status: Mapped[str] = mapped_column(String(50))
    created_at: Mapped[datetime] = mapped_column(DateTime)

    __table_args__ = (
        # Composite index — column order matters!
        Index("ix_orders_user_status", "user_id", "status"),
        # Partial index — only indexes matching rows
        Index("ix_orders_pending", "created_at",
              postgresql_where=text("status = 'pending'")),
    )
```

**Index type guide:** B-Tree (default, equality/range), GIN (full-text, JSONB), GiST (geometric), BRIN (sequential data, 100x smaller than B-tree)

### 5. N+1 Prevention

```python
from sqlalchemy import select
from sqlalchemy.orm import selectinload, joinedload

# ❌ BAD: N+1 problem — 1 query + N queries for orders
async def get_users_bad(db: AsyncSession) -> list[User]:
    stmt = select(User)
    result = await db.execute(stmt)
    users = list(result.scalars().all())
    for user in users:
        _ = await db.run_sync(lambda s: user.orders)  # N extra queries
    return users

# ✅ GOOD: selectinload — 2 queries (users + all orders in one IN clause)
async def get_users_selectin(db: AsyncSession) -> list[User]:
    stmt = select(User).options(selectinload(User.orders))
    result = await db.execute(stmt)
    return list(result.scalars().unique().all())

# ✅ GOOD: joinedload — 1 query with JOIN (best for one-to-one)
async def get_users_joined(db: AsyncSession) -> list[User]:
    stmt = select(User).options(joinedload(User.profile))
    result = await db.execute(stmt)
    return list(result.scalars().unique().all())
```

**Loading strategy:** One-to-one → `joinedload`; One-to-many (small) → `selectinload`; One-to-many (large) → `subqueryload`

### 6. Transaction Isolation (Brief)

```python
engine = create_async_engine(
    "postgresql+asyncpg://user:pass@localhost/mydb",
    isolation_level="REPEATABLE_READ",
)

# Override per unit of work
serializable_engine = engine.execution_options(isolation_level="SERIALIZABLE")
```

**Isolation levels:** READ UNCOMMITTED → READ COMMITTED → REPEATABLE READ → SERIALIZABLE (increasing safety, decreasing performance)

### 7. Repository Pattern (Brief)

```python
from abc import ABC, abstractmethod
from typing import Generic, TypeVar

T = TypeVar("T")

class AbstractRepository(ABC, Generic[T]):
    @abstractmethod
    async def add(self, entity: T) -> T: ...
    @abstractmethod
    async def get(self, entity_id: int) -> T | None: ...
    @abstractmethod
    async def list(self, *, offset: int = 0, limit: int = 100) -> Sequence[T]: ...
    @abstractmethod
    async def delete(self, entity_id: int) -> bool: ...

class SQLAlchemyRepository(AbstractRepository[T]):
    def __init__(self, session: AsyncSession, model_class: type[T]):
        self.session = session
        self.model_class = model_class

    async def add(self, entity: T) -> T:
        self.session.add(entity)
        await self.session.flush()
        return entity

    async def get(self, entity_id: int) -> T | None:
        return await self.session.get(self.model_class, entity_id)
```

---

## Best Practices

1. **Profile before optimizing** — use `EXPLAIN ANALYZE` before adding indexes
2. **Use parameterized queries** — never concatenate SQL strings (SQL injection risk)
3. **Set `pool_pre_ping=True`** — prevents errors from stale connections
4. **Always set `expire_on_commit=False`** — avoids `DetachedInstanceError` in API responses
5. **Use `selectinload` for one-to-many** — prevents N+1 without row multiplication
6. **Index foreign keys** — PostgreSQL doesn't auto-index FK columns
7. **Use partial indexes** — for columns where most rows share a value
8. **Composite index column order** — put equality columns first, range columns last
9. **Alembic for all schema changes** — never modify production schema manually
10. **Test migrations on a copy first** — `alembic upgrade head` on staging before production
11. **Use `RETURNING` clause** — get inserted data without a separate SELECT
12. **Avoid `SELECT *` in production** — specify needed columns to reduce I/O
13. **Monitor slow query log** — configure `log_min_duration_statement`
14. **Vacuum and ANALYZE regularly** — autovacuum handles most cases

---

## Common Pitfalls

| Mistake | Why It's Bad | Fix |
|---------|-------------|-----|
| `session.query()` style | Legacy 1.x API | Use `select()` 2.0 style |
| No connection pool config | DB overload on spike | Set `pool_size` + `max_overflow` |
| Missing `expire_on_commit=False` | `DetachedInstanceError` after commit | Set in `async_sessionmaker` |
| N+1 queries (lazy loading in loops) | 1000 queries for 1000 rows | Use `selectinload` / `joinedload` |
| No index on foreign keys | Full table scans on JOINs | Add `index=True` to FK columns |
| `alembic upgrade head` in prod | Unreviewed migration may break data | Review SQL, test on staging first |
| `SELECT *` for large tables | Excessive memory and network I/O | Select only needed columns |
| Over-indexing | Slows INSERT/UPDATE/DELETE | Only index queried columns |
| Composite index wrong order | Index not used for partial matches | Most selective column first |
| Auto-generate without review | May miss data migrations | Always review generated migration SQL |
| No `pool_recycle` | Stale connections after DB restart | Set `pool_recycle=1800` (30 min) |
| Mixing sync/async drivers | `asyncpg` ≠ `psycopg2` | Use `create_async_engine` with `asyncpg` |

---

## Additional Resources

- **Advanced patterns:** See [`advanced.md`](advanced.md) for deep dives, edge cases, and advanced techniques
- **Code examples:** See [`examples.md`](examples.md) for complete working examples and templates

---

## Context7 Integration

When Context7 MCP tools are available in your session, use them to fetch up-to-date library documentation instead of relying on memory. Tool names vary by installation (e.g. `mcp__context7__resolve-library-id` / `mcp__context7__query-docs`, or plugin-prefixed variants such as `mcp__plugin_context7_context7__*`) — check the available-tools listing for the exact names. Always resolve the library ID first; the IDs in the table below are examples and may change.

| Library | Context7 ID | When to Query |
|---------|-------------|---------------|
| SQLAlchemy | `/websites/sqlalchemy_en_20` | ORM patterns, session config, engine setup |
| Alembic | `/websites/alembic_sqlalchemy` | Migration patterns, autogenerate config |
| PostgreSQL | (query "PostgreSQL") | Index types, JSONB, partitioning |

**When to query:**
- Before implementing a new pattern — verify the API hasn't changed
- When encountering deprecation warnings — check for replacement APIs
- When configuring engine/session — verify current recommended defaults
- When writing migrations — check for Alembic version-specific features
