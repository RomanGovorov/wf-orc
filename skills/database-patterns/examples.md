# Code Examples: Database Patterns

> Working examples for [`SKILL.md`](SKILL.md).

## Example 1: Complete Connection Pool + FastAPI Dependency

```python
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from fastapi import FastAPI

engine = create_async_engine(
    "postgresql+asyncpg://user:pass@localhost/mydb",
    pool_size=20,
    max_overflow=10,
    pool_timeout=30,
    pool_recycle=1800,
    pool_pre_ping=True,
    echo=False,
    connect_args={"server_settings": {"application_name": "myapp"}},
)

AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)

async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise

@asynccontextmanager
async def lifespan(app: FastAPI):
    yield
    await engine.dispose()

app = FastAPI(lifespan=lifespan)
```

---

## Example 2: Full Repository Implementation

```python
from abc import ABC, abstractmethod
from typing import Generic, TypeVar, Sequence
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

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

    async def list(self, *, offset: int = 0, limit: int = 100) -> Sequence[T]:
        stmt = select(self.model_class).offset(offset).limit(limit)
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

# Specialized repository
class UserRepository(SQLAlchemyRepository[User]):
    def __init__(self, session: AsyncSession):
        super().__init__(session, User)

    async def get_by_email(self, email: str) -> User | None:
        stmt = select(User).where(User.email == email)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def search_active(self, query: str, *, offset: int = 0, limit: int = 20
    ) -> tuple[Sequence[User], int]:
        base = select(User).where(
            User.is_active == True,
            User.name.ilike(f"%{query}%"),
        )
        count_stmt = select(func.count()).select_from(base.subquery())
        total = (await self.session.execute(count_stmt)).scalar()
        stmt = base.order_by(User.created_at.desc()).offset(offset).limit(limit)
        result = await self.session.execute(stmt)
        return result.scalars().all(), total
```

---

## Example 3: FastAPI Endpoint with Repository

```python
from pydantic import BaseModel, ConfigDict
from fastapi import APIRouter, Depends

class UserRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    email: str
    name: str

class UserPage(BaseModel):
    items: list[UserRead]
    total: int
    page: int

def get_user_repository(db: AsyncSession = Depends(get_db)) -> UserRepository:
    return UserRepository(db)

@router.get("/users", response_model=UserPage)
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

## Example 4: N+1 Prevention — Nested Eager Loading

```python
from sqlalchemy import select
from sqlalchemy.orm import selectinload, joinedload

# Nested eager loading
async def get_users_with_full_tree(db: AsyncSession) -> list[User]:
    stmt = (
        select(User)
        .options(
            selectinload(User.orders)
                .selectinload(Order.items)
                .joinedload(OrderItem.product)
        )
    )
    result = await db.execute(stmt)
    return list(result.scalars().unique().all())
```

---

## Example 5: Index Types — SQL Reference

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

-- Covering index — INCLUDE for index-only scans
CREATE INDEX idx_orders_cover ON orders(user_id) INCLUDE (total, status);
```

---

## Example 6: Unit of Work Pattern

```python
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

## Example 7: CQRS with FastAPI Dependencies

```python
# FastAPI dependencies
async def get_write_db():
    async with WriteSession() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise

async def get_read_db():
    async with ReadSession() as session:
        yield session

@router.post("/orders", response_model=OrderRead)
async def create_order(data: OrderCreate, db=Depends(get_write_db)):
    handler = OrderCommandHandler(db)
    order = await handler.create_order(data)
    return order

@router.get("/orders/dashboard")
async def order_dashboard(user=Depends(get_current_user), db=Depends(get_read_db)):
    handler = OrderQueryHandler(db)
    return await handler.get_dashboard(user.id)
```

---

## Example 8: Alembic Async Migration Configuration

```python
# alembic/env.py
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

---

## Additional Resources

- **Core patterns:** See [`SKILL.md`](SKILL.md) for essential patterns
- **Advanced techniques:** See [`advanced.md`](advanced.md) for deep dives and edge cases
