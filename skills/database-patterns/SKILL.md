---
name: database-patterns
description: Database design patterns — normalization, indexing, migrations (Alembic), connection pooling, transactions, partitioning, CQRS, NoSQL. Use when designing schemas, writing queries, configuring pools, or planning migrations.
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

- **CP** (Consistency + Partition tolerance) — PostgreSQL, MySQL (single-node)
- **AP** (Availability + Partition tolerance) — Cassandra, DynamoDB
- **CA** (Consistency + Availability) — only possible without partitions (single-node, no replication)

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
# SQLAlchemy 2.0 — async engine with pool configuration
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker

engine = create_async_engine(
    "postgresql+asyncpg://user:pass@localhost/mydb",
    # Pool sizing — start with (2 * CPU_cores) + disk_spindles
    pool_size=20,           # Persistent connections in pool
    max_overflow=10,        # Extra connections during spikes (total = 30)
    pool_timeout=30,        # Seconds to wait for available connection
    pool_recycle=1800,      # Recycle connections every 30 min (prevent stale)
    pool_pre_ping=True,     # Test connection before use (catch disconnects)
    # Performance
    echo=False,             # Disable SQL logging in production
    connect_args={
        "server_settings": {"application_name": "myapp"},  # Identify in pg_stat_activity
    },
)

AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,  # Don't expire after commit — safe for API responses
)

# FastAPI dependency with proper cleanup
async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        # async with auto-closes the session

# Lifespan — dispose pool on shutdown
from contextlib import asynccontextmanager

@asynccontextmanager
async def lifespan(app: FastAPI):
    yield
    await engine.dispose()  # Close all pooled connections gracefully
```

**Pool sizing formula:**

```
connections = ((cpu_cores * 2) + effective_spindle_count)
```

- SSD/NVMe: `effective_spindle_count = 1`
- For 4-core server with SSD: `(4 * 2) + 1 = 9` connections
- **Never** set pool_size = 100 without load testing — each connection consumes RAM

---

### 2. Session Management

```python
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from sqlalchemy.orm import Mapped, mapped_column

# ✅ GOOD: expire_on_commit=False for API responses
AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)

async def get_user_with_orders(db: AsyncSession, user_id: int) -> User:
    """Session with expire_on_commit=False — attributes remain accessible after commit."""
    stmt = (
        select(User)
        .options(selectinload(User.orders))
        .where(User.id == user_id)
    )
    result = await db.execute(stmt)
    return result.scalar_one_or_none()

# ✅ GOOD: Unit of Work pattern — explicit commit boundaries
class UnitOfWork:
    """Manages transaction boundaries explicitly."""

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

# Usage
async def create_order_with_items(order_data: dict, items: list[dict]):
    async with UnitOfWork(AsyncSessionLocal) as session:
        order = Order(**order_data)
        session.add(order)
        await session.flush()  # Get order.id without committing

        for item in items:
            session.add(OrderItem(order_id=order.id, **item))
        # Commit happens on __aexit__ if no exception
```

---

### 3. Alembic Migrations

```python
# alembic/env.py — async-compatible configuration
import asyncio
from logging.config import fileConfig
from sqlalchemy.ext.asyncio import create_async_engine
from alembic import context

from myapp.models.base import Base  # Import all models!
from myapp.config import settings

config = context.config
fileConfig(config.config_file_name)
target_metadata = Base.metadata

def run_migrations_offline():
    """Generate SQL without connecting to DB."""
    context.configure(
        url=settings.DATABASE_URL,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()

def do_run_migrations(connection):
    context.configure(connection=connection, target_metadata=target_metadata)
    with context.begin_transaction():
        context.run_migrations()

async def run_async_migrations():
    """Run migrations with async engine."""
    connectable = create_async_engine(settings.DATABASE_URL)
    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)
    await connectable.dispose()

def run_migrations_online():
    asyncio.run(run_async_migrations())
```

**Branching migrations** (parallel feature branches):

```python
# alembic/versions/003a_add_user_preferences.py
"""add user preferences

Revision ID: 003a
Revises: 002
Branch point: true — this is one of two branches from 002
"""
revision = "003a"
down_revision = "002"
branch_labels = ("preferences",)
depends_on = None

def upgrade():
    op.create_table("user_preferences", ...)

# alembic/versions/003b_add_user_sessions.py
"""add user sessions

Revision ID: 003b
Revises: 002
"""
revision = "003b"
down_revision = "002"
branch_labels = ("sessions",)
depends_on = None

def upgrade():
    op.create_table("user_sessions", ...)

# alembic/versions/004_merge.py — merge branches
"""merge preferences and sessions branches

Revision ID: 004
Revises: 003a, 003b  — TWO parents
"""
revision = "004"
down_revision = ("003a", "003b")  # tuple = merge point
branch_labels = None
depends_on = None

def upgrade():
    pass  # No schema changes — just merges the DAG
```

**Data migration pattern:**

```python
# alembic/versions/005_migrate_user_roles.py
"""migrate user roles from boolean to enum

Revision ID: 005
Revises: 004
"""
from alembic import op
import sqlalchemy as sa

revision = "005"
down_revision = "004"

def upgrade():
    # 1. Add new column with default
    op.add_column(
        "users",
        sa.Column("role", sa.String(50), server_default="viewer", nullable=False),
    )
    op.create_index("ix_users_role", "users", ["role"])

    # 2. Migrate existing data
    conn = op.get_bind()
    conn.execute(sa.text("""
        UPDATE users SET role = 'admin' WHERE is_admin = true
    """))

    # 3. Drop old column
    op.drop_column("users", "is_admin")

def downgrade():
    op.add_column("users", sa.Column("is_admin", sa.Boolean(), server_default=sa.false()))
    conn = op.get_bind()
    conn.execute(sa.text("""
        UPDATE users SET is_admin = true WHERE role = 'admin'
    """))
    op.drop_index("ix_users_role", table_name="users")
    op.drop_column("users", "role")
```

---

### 4. Indexing Strategies

```python
# SQLAlchemy — index definitions on models
from sqlalchemy import Index, text

class Order(Base):
    __tablename__ = "orders"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)  # B-tree
    status: Mapped[str] = mapped_column(String(50))
    total: Mapped[Decimal] = mapped_column(Numeric(10, 2))
    created_at: Mapped[datetime] = mapped_column(DateTime)

    __table_args__ = (
        # Composite index — column order matters!
        # Works for: WHERE user_id = ? AND status = ?
        # Works for: WHERE user_id = ?
        # Does NOT work for: WHERE status = ? (skips first column)
        Index("ix_orders_user_status", "user_id", "status"),

        # Partial index — only indexes matching rows (saves space + faster writes)
        Index(
            "ix_orders_pending",
            "created_at",
            postgresql_where=text("status = 'pending'"),
        ),

        # Covering index — INCLUDE for index-only scans (no table lookup)
        Index(
            "ix_orders_email_cover",
            "user_id",
            postgresql_include=["total", "status"],
        ),
    )
```

**Index type guide:**

```sql
-- B-Tree: default, equality and range (=, <, >, BETWEEN, LIKE 'prefix%')
CREATE INDEX idx_users_email ON users(email);

-- GIN: full-text search, JSONB containment, array operations
CREATE INDEX idx_products_tags ON products USING gin(tags);
CREATE INDEX idx_docs_body ON documents USING gin(body_tsv);
CREATE INDEX idx_profiles_data ON user_profiles USING gin(data);

-- GiST: geometric, range types, nearest-neighbor search
CREATE INDEX idx_locations_geo ON locations USING gist(coordinates);

-- BRIN: naturally ordered data (timestamps, sequential IDs)
-- 100x smaller than B-tree for sequential data
CREATE INDEX idx_events_created ON events USING brin(created_at);

-- Partial: only matching rows — saves space, faster writes
CREATE INDEX idx_active_users ON users(email) WHERE is_active = true;

-- Composite: multiple columns — order = most selective first
CREATE INDEX idx_orders_user_status_date ON orders(user_id, status, created_at);
```

**When NOT to index:**
- Tables with more writes than reads
- Very small tables (< 1000 rows) — sequential scan is faster
- Columns with low cardinality (boolean, status with 2 values) — use partial index instead
- Columns that are frequently updated

---

### 5. N+1 Prevention

```python
from sqlalchemy import select
from sqlalchemy.orm import selectinload, joinedload, subqueryload

# ❌ BAD: N+1 problem — 1 query + N queries for orders
async def get_users_bad(db: AsyncSession) -> list[User]:
    stmt = select(User)
    result = await db.execute(stmt)
    users = list(result.scalars().all())
    for user in users:
        _ = user.orders  # LAZY LOAD — fires a separate query per user!
    return users

# ✅ GOOD: selectinload — 2 queries (users + all orders in one IN clause)
# Best for: one-to-many relationships (user → orders)
async def get_users_selectin(db: AsyncSession) -> list[User]:
    stmt = select(User).options(selectinload(User.orders))
    result = await db.execute(stmt)
    return list(result.scalars().unique().all())

# ✅ GOOD: joinedload — 1 query with JOIN
# Best for: one-to-one relationships (user → profile)
# ⚠️ Caution with one-to-many: multiplies rows (Cartesian product)
async def get_users_joined(db: AsyncSession) -> list[User]:
    stmt = select(User).options(joinedload(User.profile))
    result = await db.execute(stmt)
    return list(result.scalars().unique().all())

# ✅ GOOD: subqueryload — 2 queries (users + subquery for orders)
# Best for: large collections where IN clause would be too big
async def get_users_subquery(db: AsyncSession) -> list[User]:
    stmt = select(User).options(subqueryload(User.orders))
    result = await db.execute(stmt)
    return list(result.scalars().unique().all())

# Loading strategy guide:
# | Relationship     | Strategy        | Why                                    |
# |------------------|-----------------|----------------------------------------|
# | One-to-one       | joinedload      | Single JOIN, no row multiplication     |
# | One-to-many (small)| selectinload  | Efficient IN clause, separate query    |
# | One-to-many (large)| subqueryload  | Avoids huge IN clause                  |
# | Many-to-many     | selectinload    | Handles junction table efficiently     |

# ✅ GOOD: Nested eager loading
async def get_users_with_full_tree(db: AsyncSession) -> list[User]:
    stmt = (
        select(User)
        .options(
            selectinload(User.orders).selectinload(Order.items).joinedload(OrderItem.product)
        )
    )
    result = await db.execute(stmt)
    return list(result.scalars().unique().all())
```

---

### 6. Transaction Isolation

```python
from sqlalchemy.ext.asyncio import create_async_engine

# Configure default isolation level at engine level
engine = create_async_engine(
    "postgresql+asyncpg://user:pass@localhost/mydb",
    isolation_level="REPEATABLE_READ",  # Default for all connections
)

# Override per-transaction
from sqlalchemy import event

async def transfer_funds(
    db: AsyncSession,
    from_account: int,
    to_account: int,
    amount: Decimal,
):
    """Transfer with SERIALIZABLE isolation — prevents all anomalies."""
    # Start explicit transaction with specific isolation level
    await db.execute(
        text("SET TRANSACTION ISOLATION LEVEL SERIALIZABLE")
    )

    # Read current balances (repeatable within this transaction)
    sender = await db.get(Account, from_account)
    receiver = await db.get(Account, to_account)

    if sender.balance < amount:
        raise InsufficientFundsError()

    sender.balance -= amount
    receiver.balance += amount
    await db.commit()

# Isolation levels comparison:
# | Level             | Dirty Read | Non-repeatable Read | Phantom Read | Performance |
# |-------------------|:----------:|:-------------------:|:------------:|:-----------:|
# | READ UNCOMMITTED  |  Possible  |     Possible        |   Possible   |   Fastest   |
# | READ COMMITTED    | Prevented  |     Possible        |   Possible   |   Fast      |
# | REPEATABLE READ   | Prevented  |     Prevented       |   Possible*  |   Medium    |
# | SERIALIZABLE      | Prevented  |     Prevented       |   Prevented  |   Slowest   |
# * PostgreSQL REPEATABLE READ also prevents phantom reads

# ✅ GOOD: Optimistic locking with version column
class Account(Base):
    __tablename__ = "accounts"
    id: Mapped[int] = mapped_column(primary_key=True)
    balance: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    version: Mapped[int] = mapped_column(Integer, default=0)

    __mapper_args__ = {"version_id_col": "version"}
    # SQLAlchemy automatically adds WHERE version = ? to UPDATE statements
    # Raises StaleDataError if version doesn't match → retry the operation
```

---

### 7. CQRS Pattern

```python
from typing import Protocol, Generic, TypeVar
from sqlalchemy.ext.asyncio import AsyncSession

T = TypeVar("T")

# Write model — optimized for consistency and business rules
class CommandModel(Protocol, Generic[T]):
    async def create(self, entity: T) -> T: ...
    async def update(self, entity: T) -> T: ...
    async def delete(self, entity_id: int) -> None: ...

# Read model — optimized for query performance
class QueryModel(Protocol, Generic[T]):
    async def get_by_id(self, entity_id: int) -> T | None: ...
    async def search(self, filters: dict) -> list[T]: ...
    async def list_paginated(self, page: int, size: int) -> tuple[list[T], int]: ...

# Write side — separate engine/session for writes
write_engine = create_async_engine(
    "postgresql+asyncpg://user:pass@primary-host/mydb",
    pool_size=10,
)
WriteSession = async_sessionmaker(write_engine, class_=AsyncSession, expire_on_commit=False)

# Read side — separate engine/session for reads (can point to replica)
read_engine = create_async_engine(
    "postgresql+asyncpg://user:pass@replica-host/mydb",
    pool_size=30,  # More connections for reads
)
ReadSession = async_sessionmaker(read_engine, class_=AsyncSession)

# Command handler
class OrderCommandHandler:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create_order(self, data: OrderCreate) -> Order:
        order = Order(**data.model_dump())
        self.session.add(order)
        await self.session.flush()

        for item in data.items:
            self.session.add(OrderItem(order_id=order.id, **item.model_dump()))

        return order

# Query handler — can use raw SQL for complex reads
class OrderQueryHandler:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_dashboard(self, user_id: int) -> dict:
        """Denormalized read — returns everything the dashboard needs."""
        result = await self.session.execute(text("""
            SELECT
                o.id, o.status, o.total, o.created_at,
                COUNT(oi.id) as item_count,
                SUM(oi.quantity * oi.price) as computed_total
            FROM orders o
            LEFT JOIN order_items oi ON oi.order_id = o.id
            WHERE o.user_id = :user_id
            GROUP BY o.id
            ORDER BY o.created_at DESC
            LIMIT 20
        """), {"user_id": user_id})
        return [dict(row._mapping) for row in result]

# FastAPI dependencies
async def get_write_db():
    async with WriteSession() as session:
        yield session

async def get_read_db():
    async with ReadSession() as session:
        yield session

@router.post("/orders")
async def create_order(data: OrderCreate, db=Depends(get_write_db)):
    handler = OrderCommandHandler(db)
    return await handler.create_order(data)

@router.get("/orders/dashboard")
async def order_dashboard(user=Depends(get_current_user), db=Depends(get_read_db)):
    handler = OrderQueryHandler(db)
    return await handler.get_dashboard(user.id)
```

---

### 8. Repository Pattern

```python
from abc import ABC, abstractmethod
from typing import Generic, TypeVar, Sequence
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

T = TypeVar("T")

class AbstractRepository(ABC, Generic[T]):
    """Abstract base — depends on abstractions, not implementations."""

    @abstractmethod
    async def add(self, entity: T) -> T: ...

    @abstractmethod
    async def get(self, entity_id: int) -> T | None: ...

    @abstractmethod
    async def list(self, *, offset: int = 0, limit: int = 100) -> Sequence[T]: ...

    @abstractmethod
    async def delete(self, entity_id: int) -> bool: ...


class SQLAlchemyRepository(AbstractRepository[T]):
    """Concrete implementation for SQLAlchemy async sessions."""

    def __init__(self, session: AsyncSession, model_class: type[T]):
        self.session = session
        self.model_class = model_class

    async def add(self, entity: T) -> T:
        self.session.add(entity)
        await self.session.flush()
        return entity

    async def get(self, entity_id: int) -> T | None:
        return await self.session.get(self.model_class, entity_id)

    async def list(self, *, offset: int = 0, limit: int = 100) -> Sequence[T]:
        stmt = (
            select(self.model_class)
            .offset(offset)
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def count(self) -> int:
        stmt = select(func.count()).select_from(self.model_class)
        result = await self.session.execute(stmt)
        return result.scalar()

    async def delete(self, entity_id: int) -> bool:
        entity = await self.get(entity_id)
        if entity is None:
            return False
        await self.session.delete(entity)
        await self.session.flush()
        return True


# Specialized repository with domain-specific queries
class UserRepository(SQLAlchemyRepository[User]):
    def __init__(self, session: AsyncSession):
        super().__init__(session, User)

    async def get_by_email(self, email: str) -> User | None:
        stmt = select(User).where(User.email == email)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def search_active(
        self, query: str, *, offset: int = 0, limit: int = 20
    ) -> tuple[Sequence[User], int]:
        """Search active users with pagination."""
        base = select(User).where(
            User.is_active == True,
            User.name.ilike(f"%{query}%"),
        )
        count_stmt = select(func.count()).select_from(base.subquery())
        total = (await self.session.execute(count_stmt)).scalar()

        stmt = base.order_by(User.created_at.desc()).offset(offset).limit(limit)
        result = await self.session.execute(stmt)
        return result.scalars().all(), total


# FastAPI dependency injection
def get_user_repository(db: AsyncSession = Depends(get_db)) -> UserRepository:
    return UserRepository(db)

@router.get("/users")
async def list_users(
    search: str | None = None,
    page: int = 1,
    repo: UserRepository = Depends(get_user_repository),
):
    if search:
        users, total = await repo.search_active(search, offset=(page - 1) * 20)
    else:
        users = await repo.list(offset=(page - 1) * 20)
        total = await repo.count()
    return {"items": users, "total": total, "page": page}
```

---

### 9. Soft Delete Pattern

```python
from sqlalchemy import Boolean, DateTime, select, func
from sqlalchemy.orm import Mapped, mapped_column, Query
from datetime import datetime, timezone

class SoftDeleteMixin:
    """Mixin for soft-delete support — rows are marked as deleted, not removed."""

    is_deleted: Mapped[bool] = mapped_column(
        Boolean, default=False, index=True,
    )
    deleted_at: Mapped[datetime | None] = mapped_column(
        DateTime, nullable=True, default=None,
    )


class User(Base, SoftDeleteMixin, TimestampMixin):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100))
    email: Mapped[str] = mapped_column(String(255), unique=True)


# ✅ GOOD: Default filter excludes soft-deleted rows
class SoftDeleteRepository(SQLAlchemyRepository[T]):
    """Repository that automatically filters out soft-deleted records."""

    async def list(self, *, offset: int = 0, limit: int = 100) -> Sequence[T]:
        stmt = (
            select(self.model_class)
            .where(self.model_class.is_deleted == False)
            .offset(offset)
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def soft_delete(self, entity_id: int) -> bool:
        entity = await self.session.get(self.model_class, entity_id)
        if entity is None or entity.is_deleted:
            return False
        entity.is_deleted = True
        entity.deleted_at = datetime.now(timezone.utc)
        await self.session.flush()
        return True

    async def restore(self, entity_id: int) -> bool:
        """Restore a soft-deleted record."""
        stmt = select(self.model_class).where(
            self.model_class.id == entity_id,
            self.model_class.is_deleted == True,
        )
        result = await self.session.execute(stmt)
        entity = result.scalar_one_or_none()
        if entity is None:
            return False
        entity.is_deleted = False
        entity.deleted_at = None
        await self.session.flush()
        return True

    async def hard_delete(self, entity_id: int) -> bool:
        """Permanently delete a record — use with caution."""
        entity = await self.session.get(self.model_class, entity_id)
        if entity is None:
            return False
        await self.session.delete(entity)
        await self.session.flush()
        return True

# Partial index for efficient soft-delete filtering
# CREATE INDEX ix_users_not_deleted ON users(id) WHERE is_deleted = false;
```

---

### 10. Bulk Operations

```python
from sqlalchemy import insert, update, text
from sqlalchemy.dialects.postgresql import insert as pg_insert

# ✅ GOOD: Batch INSERT — single round-trip
async def bulk_insert_orders(db: AsyncSession, orders: list[dict]):
    """Insert multiple rows in one query."""
    await db.execute(insert(Order), orders)
    # Auto-commits at session boundary

# ✅ GOOD: Upsert (INSERT ... ON CONFLICT UPDATE) — PostgreSQL
async def upsert_products(db: AsyncSession, products: list[dict]):
    """Insert or update products based on unique constraint."""
    stmt = pg_insert(Product).values(products)
    stmt = stmt.on_conflict_do_update(
        index_elements=["sku"],  # Unique constraint column
        set_={
            "name": stmt.excluded.name,
            "price": stmt.excluded.price,
            "stock": stmt.excluded.stock,
            "updated_at": func.now(),
        },
    )
    await db.execute(stmt)

# ✅ GOOD: Batch UPDATE — update multiple rows efficiently
async def bulk_update_status(db: AsyncSession, order_ids: list[int], new_status: str):
    """Update status for multiple orders."""
    stmt = (
        update(Order)
        .where(Order.id.in_(order_ids))
        .values(status=new_status, updated_at=func.now())
    )
    await db.execute(stmt)

# ✅ GOOD: Chunked processing for very large datasets
async def chunked_insert(
    db: AsyncSession,
    model_class: type,
    records: list[dict],
    chunk_size: int = 1000,
):
    """Insert in chunks to avoid memory pressure and lock contention."""
    for i in range(0, len(records), chunk_size):
        chunk = records[i:i + chunk_size]
        await db.execute(insert(model_class), chunk)
        await db.commit()  # Commit per chunk to release locks

# ✅ GOOD: COPY for massive data loads (PostgreSQL)
async def copy_load_csv(db: AsyncSession, table_name: str, csv_path: str):
    """Use PostgreSQL COPY for fastest bulk loading."""
    conn = await db.connection()
    await conn.run_sync(
        lambda sync_conn: sync_conn.execute(
            text(f"COPY {table_name} FROM :path WITH (FORMAT csv, HEADER true)"),
            {"path": csv_path},
        )
    )
```

---

## Best Practices

1. **Profile before optimizing** — use `EXPLAIN ANALYZE` before adding indexes
2. **Use parameterized queries** — never concatenate SQL strings (SQL injection risk)
3. **Set `pool_pre_ping=True`** — prevents errors from stale connections after DB restart
4. **Always set `expire_on_commit=False`** — avoids `DetachedInstanceError` in API responses
5. **Use `selectinload` for one-to-many** — prevents N+1 without row multiplication
6. **Index foreign keys** — PostgreSQL doesn't auto-index FK columns
7. **Use partial indexes** — for columns where most rows share a value (e.g., `WHERE status != 'archived'`)
8. **Composite index column order** — put equality columns first, range columns last
9. **Alembic for all schema changes** — never modify production schema manually
10. **Test migrations on a copy first** — `alembic upgrade head` on staging before production
11. **Use `RETURNING` clause** — get inserted data without a separate SELECT
12. **Avoid `SELECT *` in production** — specify needed columns to reduce I/O
13. **Monitor slow query log** — configure `log_min_duration_statement` in PostgreSQL
14. **Vacuum and ANALYZE regularly** — PostgreSQL autovacuum handles most cases, but large tables need manual tuning

## Common Pitfalls

| Mistake | Why It's Bad | Fix |
|---------|-------------|-----|
| `session.query()` style | Deprecated 1.x API — removed in future | Use `select()` 2.0 style |
| No connection pool config | DB overload on spike | Set `pool_size` + `max_overflow` |
| Missing `expire_on_commit=False` | `DetachedInstanceError` after commit | Set in `async_sessionmaker` |
| N+1 queries (lazy loading in loops) | 1000 queries for 1000 rows | Use `selectinload` / `joinedload` |
| No index on foreign keys | Full table scans on JOINs | Add `index=True` to FK columns |
| `alembic upgrade head` in prod | Unreviewed migration may break data | Review SQL, test on staging first |
| `SELECT *` for large tables | Excessive memory and network I/O | Select only needed columns |
| Over-indexing | Slows INSERT/UPDATE/DELETE | Only index queried columns |
| Composite index wrong order | Index not used for partial matches | Most selective column first |
| Auto-generate without review | May miss data migrations or complex changes | Always review generated migration SQL |
| No `pool_recycle` | Stale connections after DB restart | Set `pool_recycle=1800` (30 min) |
| Mixing sync/async drivers | `asyncpg` ≠ `psycopg2` | Use `create_async_engine` with `asyncpg` |

---

## Context7 Integration

When working with database patterns, verify against current documentation:

| Library | Context7 ID | When to Query |
|---------|-------------|---------------|
| SQLAlchemy | `/websites/sqlalchemy_en_20` | ORM patterns, session config, engine setup |
| Alembic | `/websites/alembic_sqlalchemy` | Migration patterns, autogenerate config |
| PostgreSQL | (query "PostgreSQL") | Index types, JSONB, partitioning |

Use `mcp__context7__resolve-library-id` then `mcp__context7__query-docs` to get current examples.

**When to query:**
- Before implementing a new pattern — verify the API hasn't changed
- When encountering deprecation warnings — check for replacement APIs
- When configuring engine/session — verify current recommended defaults
- When writing migrations — check for Alembic version-specific features
