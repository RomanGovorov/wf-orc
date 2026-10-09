# Advanced Patterns: Database Patterns

> This file extends [`SKILL.md`](SKILL.md) with advanced patterns and edge cases.

## CQRS Pattern

Separate read and write models for optimal performance.

```python
from typing import Protocol, Generic, TypeVar
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

T = TypeVar("T")

# Write model — optimized for consistency
class CommandModel(Protocol, Generic[T]):
    async def create(self, entity: T) -> T: ...
    async def update(self, entity: T) -> T: ...
    async def delete(self, entity_id: int) -> None: ...

# Read model — optimized for query performance
class QueryModel(Protocol, Generic[T]):
    async def get_by_id(self, entity_id: int) -> T | None: ...
    async def search(self, filters: dict) -> list[T]: ...
    async def list_paginated(self, page: int, size: int) -> tuple[list[T], int]: ...

# Write side — separate engine/session
write_engine = create_async_engine(
    "postgresql+asyncpg://user:pass@primary-host/mydb",
    pool_size=10,
)
WriteSession = async_sessionmaker(write_engine, class_=AsyncSession, expire_on_commit=False)

# Read side — can point to replica
read_engine = create_async_engine(
    "postgresql+asyncpg://user:pass@replica-host/mydb",
    pool_size=30,  # More connections for reads
)
ReadSession = async_sessionmaker(read_engine, class_=AsyncSession, expire_on_commit=False)

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

    async def get_dashboard(self, user_id: int) -> list[dict]:
        result = await self.session.execute(text("""
            SELECT o.id, o.status, o.total, o.created_at,
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
```

---

## Soft Delete Pattern

```python
from sqlalchemy import Boolean, DateTime, select, func, text
from sqlalchemy.orm import Mapped, mapped_column
from datetime import datetime, timezone

class SoftDeleteMixin:
    is_deleted: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    deleted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True, default=None,
    )

class User(Base, SoftDeleteMixin):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100))
    email: Mapped[str] = mapped_column(String(255), index=True)

    __table_args__ = (
        # Partial unique index — only enforced among non-deleted rows
        Index("uq_users_email_active", "email", unique=True,
              postgresql_where=text("is_deleted = false")),
    )

class SoftDeleteRepository(SQLAlchemyRepository[T]):
    async def list(self, *, offset: int = 0, limit: int = 100) -> Sequence[T]:
        stmt = (
            select(self.model_class)
            .where(self.model_class.is_deleted == False)
            .offset(offset).limit(limit)
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
```

---

## Bulk Operations

```python
from sqlalchemy import insert, update
from sqlalchemy.dialects.postgresql import insert as pg_insert

# Batch INSERT — single round-trip
async def bulk_insert_orders(db: AsyncSession, orders: list[dict]):
    await db.execute(insert(Order), orders)
    await db.commit()

# Upsert (INSERT ... ON CONFLICT UPDATE) — PostgreSQL
async def upsert_products(db: AsyncSession, products: list[dict]):
    stmt = pg_insert(Product).values(products)
    stmt = stmt.on_conflict_do_update(
        index_elements=["sku"],
        set_={
            "name": stmt.excluded.name,
            "price": stmt.excluded.price,
            "stock": stmt.excluded.stock,
            "updated_at": func.now(),
        },
    )
    await db.execute(stmt)

# Batch UPDATE
async def bulk_update_status(db: AsyncSession, order_ids: list[int], new_status: str):
    stmt = (
        update(Order)
        .where(Order.id.in_(order_ids))
        .values(status=new_status, updated_at=func.now())
    )
    await db.execute(stmt)

# Chunked processing for very large datasets
async def chunked_insert(db: AsyncSession, model_class: type, records: list[dict], chunk_size: int = 1000):
    for i in range(0, len(records), chunk_size):
        chunk = records[i:i + chunk_size]
        await db.execute(insert(model_class), chunk)
        await db.commit()  # Commit per chunk to release locks

# COPY for massive data loads (PostgreSQL)
async def copy_load_records(db: AsyncSession, table_name: str, records: list[tuple]):
    allowed_tables = {"orders", "products", "events"}
    if table_name not in allowed_tables:
        raise ValueError(f"Table not allowed for COPY load: {table_name}")

    conn = await db.connection()
    raw = await conn.get_raw_connection()
    asyncpg_conn = raw.driver_connection
    await asyncpg_conn.copy_records_to_table(table_name, records=records)
```

---

## Transaction Isolation — Full Example

```python
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy.exc import OperationalError
import asyncio

engine = create_async_engine(
    "postgresql+asyncpg://user:pass@localhost/mydb",
    isolation_level="REPEATABLE_READ",
)

serializable_engine = engine.execution_options(isolation_level="SERIALIZABLE")

async def transfer_funds(
    db: AsyncSession,
    from_account: int,
    to_account: int,
    amount: Decimal,
    *,
    max_retries: int = 3,
):
    """Transfer with SERIALIZABLE isolation — prevents all anomalies.

    SERIALIZABLE transactions may fail with serialization failures when
    concurrent transactions touch the same rows. Caller MUST retry.
    """
    for attempt in range(max_retries):
        try:
            sender = await db.get(Account, from_account)
            receiver = await db.get(Account, to_account)

            if sender.balance < amount:
                raise InsufficientFundsError()

            sender.balance -= amount
            receiver.balance += amount
            await db.commit()
            return
        except OperationalError:
            await db.rollback()
            if attempt == max_retries - 1:
                raise
            await asyncio.sleep(0.05 * (2 ** attempt))

# Isolation levels comparison:
# | Level             | Dirty Read | Non-repeatable Read | Phantom Read | Performance |
# |-------------------|:----------:|:-------------------:|:------------:|:-----------:|
# | READ UNCOMMITTED  |  Possible  |     Possible        |   Possible   |   Fastest   |
# | READ COMMITTED    | Prevented  |     Possible        |   Possible   |   Fast      |
# | REPEATABLE READ   | Prevented  |     Prevented       |   Possible*  |   Medium    |
# | SERIALIZABLE      | Prevented  |     Prevented       |   Prevented  |   Slowest   |
# * PostgreSQL REPEATABLE READ also prevents phantom reads
```

---

## Optimistic Locking with Version Column

```python
from sqlalchemy import Integer

class Account(Base):
    __tablename__ = "accounts"
    id: Mapped[int] = mapped_column(primary_key=True)
    balance: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    version: Mapped[int] = mapped_column(Integer, default=0)

    # version_id_col takes the mapped Column OBJECT
    __mapper_args__ = {"version_id_col": version}
    # SQLAlchemy automatically adds WHERE version = ? to UPDATE statements
    # Raises StaleDataError if version doesn't match → retry the operation
```

---

## Branching Migrations (Parallel Feature Branches)

```python
# alembic/versions/003a_add_user_preferences.py
revision = "003a"
down_revision = "002"
branch_labels = ("preferences",)

def upgrade():
    op.create_table("user_preferences", ...)

# alembic/versions/003b_add_user_sessions.py
revision = "003b"
down_revision = "002"
branch_labels = ("sessions",)

def upgrade():
    op.create_table("user_sessions", ...)

# alembic/versions/004_merge.py — merge branches
revision = "004"
down_revision = ("003a", "003b")  # tuple = merge point

def upgrade():
    pass  # No schema changes — just merges the DAG
```

---

## Data Migration Pattern

```python
# alembic/versions/005_migrate_user_roles.py
revision = "005"
down_revision = "004"

def upgrade():
    # WARNING: For large tables, adding nullable=False with server_default in one step
    # rewrites all rows (table lock). Safe pattern: (1) add nullable column, (2) backfill,
    # (3) ALTER to NOT NULL, (4) drop default.

    # 1. Add new column with default
    op.add_column("users",
        sa.Column("role", sa.String(50), server_default="viewer", nullable=False))
    op.create_index("ix_users_role", "users", ["role"])

    # 2. Migrate existing data
    conn = op.get_bind()
    conn.execute(sa.text("UPDATE users SET role = 'admin' WHERE is_admin = true"))

    # 3. Drop old column
    op.drop_column("users", "is_admin")

def downgrade():
    op.add_column("users", sa.Column("is_admin", sa.Boolean(), server_default=sa.false()))
    conn = op.get_bind()
    conn.execute(sa.text("UPDATE users SET is_admin = true WHERE role = 'admin'"))
    op.drop_index("ix_users_role", table_name="users")
    op.drop_column("users", "role")
```

---

## Additional Resources

- **Core patterns:** See [`SKILL.md`](SKILL.md) for essential patterns
- **Code examples:** See [`examples.md`](examples.md) for complete working examples
