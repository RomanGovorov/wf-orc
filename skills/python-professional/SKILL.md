---
name: python-professional
description: Professional Python — code style, FastAPI, MCP, Alembic, Jinja, SQLAlchemy 2.0. Use when writing, reviewing, and refactoring Python code.
priority: 10
paths:
  - "**/*.py"
  - "**/*.pyi"
  - "**/src/**/*.py"
  - "**/lib/**/*.py"
  - "pyproject.toml"
  - "setup.cfg"
  - "setup.py"
  - "requirements*.txt"
  - "Pipfile"
  - "alembic.ini"
  - "alembic/**"
  - "**/django/**"
  - "**/flask/**"
  - "**/fastapi/**"
  - "**/celery*"
  - "**/pydantic/**"
  - "**/jinja*/**"
  - "**/tox.ini"
  - "**/.flake8"
  - "**/ruff.toml"
---

# Python Professional

Complete guide to professional Python development — code style, FastAPI, MCP, Alembic, Jinja, SQLAlchemy 2.0, async patterns.

## When to Use This Skill

- When writing new Python code
- When reviewing Python code
- When refactoring legacy Python
- When setting up a FastAPI application
- When creating database migrations
- When working with MCP (Model Context Protocol)
- When creating HTML/XML templates
- When designing ORM models

## Core Concepts

- **src layout** — source code in `src/myapp/`, configuration in `pyproject.toml`
- **Type hints** — all functions and variables are typed (PEP 484+)
- **Ruff** — unified linter/formatter (replaces flake8 + isort + black)
- **Pydantic v2** — data validation via `BaseModel`, `ConfigDict`, `field_validator`
- **SQLAlchemy 2.0** — `select()` style, `Mapped[]`, `mapped_column()`, async sessions
- **FastAPI** — dependency injection, lifespan, middleware, async endpoints
- **Alembic** — automatic database migrations with autogenerate
- **Structured logging** — see `observability-patterns` skill for `structlog`, request correlation, OpenTelemetry

## Patterns

### 1. Code Style

### Project Structure

```
myproject/
├── pyproject.toml          # Build config, dependencies
├── README.md
├── .env.example
├── alembic.ini
├── alembic/
│   ├── env.py
│   ├── script.py.mako
│   └── versions/
├── src/
│   └── myapp/
│       ├── __init__.py
│       ├── main.py          # FastAPI app entry point
│       ├── config.py        # Settings (pydantic-settings)
│       ├── api/
│       │   ├── __init__.py
│       │   ├── deps.py      # Dependencies
│       │   └── v1/
│       │       ├── router.py
│       │       └── endpoints/
│       │           ├── users.py
│       │           ├── auth.py
│       │           └── orders.py
│       ├── core/
│       │   ├── security.py
│       │   └── db.py
│       ├── models/
│       │   ├── base.py
│       │   ├── user.py
│       │   └── order.py
│       ├── schemas/
│       │   ├── user.py
│       │   └── order.py
│       ├── services/
│       │   ├── user_service.py
│       │   └── email_service.py
│       └── templates/
│           └── email.html
├── tests/
│   ├── conftest.py
│   ├── test_api/
│   ├── test_services/
│   └── integration/
└── scripts/
    └── seed_db.py
```

### Code Style Tools

```toml
# pyproject.toml
[tool.ruff]
target-version = "py312"  # floor — bump to "py313"/"py314" as your minimum runtime advances
line-length = 100
src = ["src"]

[tool.ruff.lint]
select = [
    "E",    # pycodestyle errors
    "F",    # pyflakes
    "I",    # isort
    "N",    # pep8-naming
    "UP",   # pyupgrade
    "B",    # flake8-bugbear
    "SIM",  # flake8-simplify
    "S",    # flake8-bandit (security)
    "ARG",  # flake8-unused-arguments
    "RUF",  # ruff-specific
    "TC",   # flake8-type-checking ("TCH" prefix is deprecated — use "TC")
    "PTH",  # flake8-use-pathlib
    "ERA",  # eradicate (dead code)
]
ignore = [
    "E501",  # line length — formatter handles this
]

[tool.ruff.lint.per-file-ignores]
"tests/**" = ["S101", "ARG"]  # allow assert, unused args (recursive — covers tests/test_api/ etc.)

[tool.mypy]
python_version = "3.12"  # floor; keep in sync with ruff target-version
warn_return_any = true
warn_unused_configs = true
disallow_untyped_defs = true
disallow_incomplete_defs = true
strict_equality = true
plugins = ["pydantic.mypy"]

[[tool.mypy.overrides]]
module = ["tests.*"]
disallow_untyped_defs = false
```

Ruff/mypy pin Python 3.12 as the *floor*, not the current release — Python 3.13/3.14 are out; bump `target-version` and `python_version` together when your minimum supported runtime advances.

### Type Hints Patterns

```python
from typing import Any

# ✅ GOOD
def get_user(user_id: int) -> User | None: ...
def process(data: list[str]) -> dict[str, Any]: ...

# Python 3.12+ type alias
type UserId = int
type JsonDict = dict[str, Any]
type QueryResult = list[dict[str, Any]] | None
```

### Naming Conventions

```python
# Classes — PascalCase
class UserRepository: ...

# Functions/variables — snake_case
def get_user_by_email(email: str): ...
user_count: int = 0

# Constants — UPPER_SNAKE_CASE
MAX_RETRY = 3
DEFAULT_PAGE_SIZE = 20

# Private — leading underscore
def _internal_helper(): ...

# Modules — short_snake_case
# file: user_repo.py
```

### Docstrings (Google Style)

```python
async def create_user(
    db: AsyncSession,
    data: UserCreate,
    *,
    send_welcome_email: bool = True,
) -> User:
    """Create a new user and optionally send welcome email.

    Args:
        db: Active database session.
        data: Validated user creation data.
        send_welcome_email: If True, send welcome email after creation.

    Returns:
        Newly created User ORM model instance.

    Raises:
        ValidationError: If email already exists.
        ServiceError: If email sending fails.

    Example:
        >>> user = await create_user(db, UserCreate(email="test@test.com", name="Test"))
        >>> user.id is not None
        True
    """
    ...
```

---

### 2. FastAPI

### Application Factory

```python
# src/myapp/api/router.py
from fastapi import APIRouter

router = APIRouter(prefix="/api/v1")

from .endpoints import users, auth, orders

router.include_router(auth.router, prefix="/auth", tags=["auth"])
router.include_router(users.router, prefix="/users", tags=["users"])
router.include_router(orders.router, prefix="/orders", tags=["orders"])
```

```python
# src/myapp/main.py — Application factory
from contextlib import asynccontextmanager

from fastapi import FastAPI

from myapp.core.db import db_engine  # async engine, created in core/db.py


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup / shutdown events."""
    # Startup — verify DB is reachable; connection returns to the pool
    async with db_engine.connect():
        pass
    yield
    # Shutdown — dispose pooled connections
    await db_engine.dispose()


def create_app() -> FastAPI:
    """Application factory — build a fully configured app instance."""
    app = FastAPI(title="MyApp", lifespan=lifespan)

    from .api.router import router  # deferred import — avoids import cycles

    app.include_router(router)
    return app


app = create_app()
```

### Dependency Injection

```python
# src/myapp/api/deps.py
# (defined elsewhere: `async_session` — from core/db.py; `oauth2_scheme` —
# from core/security.py; `User` — from models/user.py; `verify_token` — from
# core/security.py / secure-coding-patterns skill; `router` — from api/router.py)
from fastapi import Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

# Database session
# NOTE: this variant NEVER commits — commit responsibility must be explicit in
# services/endpoints. RECOMMENDED: commit-on-success inside the dependency
# (commit after yield, rollback on exception) — see `database-patterns` skill.
async def get_db():
    """Provide database session — auto-cleanup via async context manager."""
    async with async_session() as session:
        yield session

# Auth dependency
async def get_current_user(
    db: AsyncSession = Depends(get_db),
    token: str = Depends(oauth2_scheme),
) -> User:
    """Verify JWT token and return current user.

    Note: `sub` is stored as str(user.id) in the JWT (secure-coding pattern),
    but User.id is Mapped[int]. Convert before the lookup; on asyncpg the bind
    type must match the column type or you get InterfaceError.
    """
    payload = verify_token(token)  # from secure-coding-patterns; returns claims dict
    try:
        user_id = int(payload["sub"])
    except (KeyError, ValueError, TypeError):
        raise HTTPException(status_code=401, detail="Invalid token")
    user = await db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid user")
    return user

# Role-based auth
async def require_admin(
    current_user: User = Depends(get_current_user),
) -> User:
    """Require admin role."""
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin role required")
    return current_user

# Usage
@router.delete("/users/{user_id}")
async def delete_user(
    user_id: int,
    db = Depends(get_db),
    admin = Depends(require_admin),
):
    ...
```

### Background Tasks

```python
# (defined elsewhere: `email_service` — from services/email_service.py;
# `user_service` — from services/user_service.py; `UserCreate` — from
# schemas/user.py; `Depends`, `get_db` — from api/deps.py; `router` — from
# api/v1/router.py)
from fastapi import BackgroundTasks
from pydantic import BaseModel, ConfigDict

class UserRead(BaseModel):
    """API response schema — endpoints return schemas, never raw ORM objects."""
    model_config = ConfigDict(from_attributes=True)

    id: int
    email: str
    name: str

async def send_welcome_email(email: str):
    """Background task — send email asynchronously.

    NOTE: receives a plain string, NOT a User ORM object. Background tasks
    run after the request's DB session closes — passing an ORM object would
    raise DetachedInstanceError on any lazy attribute access. Always pass
    plain values (user.id, user.email) extracted before the task is queued.
    """
    await email_service.send(email, "Welcome!", template="welcome")

@router.post("/users", response_model=UserRead)
async def create_user(
    data: UserCreate,
    background_tasks: BackgroundTasks,
    db = Depends(get_db),
):
    user = await user_service.create(db, data)
    # Pass plain values — the session closes before the background task runs,
    # so ORM objects would be detached and lazy loads would fail.
    background_tasks.add_task(send_welcome_email, user.email)
    return user  # serialized through UserRead (from_attributes=True)
```

### Middleware

```python
# (defined elsewhere: `app` — FastAPI app instance from main.py; `time` — import time)
from fastapi import Request
import time

@app.middleware("http")
async def add_timing_header(request: Request, call_next):
    start = time.perf_counter()
    response = await call_next(request)
    response.headers["X-Response-Time"] = f"{time.perf_counter() - start:.3f}s"
    return response
```

> **See also**: `api-design-principles` — REST/GraphQL patterns, pagination, versioning, error handling. `secure-coding-patterns` — JWT auth, CSRF, input validation for FastAPI endpoints.

---

### 3. SQLAlchemy 2.0

### Modern Model Definition

```python
# src/myapp/models/base.py
from sqlalchemy.orm import DeclarativeBase, mapped_column, Mapped
from sqlalchemy import DateTime, func
from datetime import datetime

class Base(DeclarativeBase):
    """Base ORM model."""
    pass

class TimestampMixin:
    """Mixin for models with created_at/updated_at."""
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )
```

```python
# src/myapp/models/user.py
from sqlalchemy import String, Boolean, Text
from sqlalchemy.orm import mapped_column, Mapped, relationship

class User(Base, TimestampMixin):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100))
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    hashed_password: Mapped[str] = mapped_column(String(255))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    bio: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Relationships
    orders: Mapped[list["Order"]] = relationship(
        "Order",
        back_populates="user",
        cascade="all, delete-orphan"
    )
    profile: Mapped["UserProfile" | None] = relationship(
        "UserProfile",
        back_populates="user",
        uselist=False
    )
```

### Modern Query Patterns (SQLAlchemy 2.0)

```python
from sqlalchemy import select, func
from sqlalchemy.orm import selectinload

# ✅ GOOD: Modern 2.0 style
async def get_users(
    db: AsyncSession,
    page: int = 1,
    page_size: int = 20,
    search: str | None = None,
) -> tuple[list[User], int]:
    """Get paginated users with optional search."""
    # Base query
    stmt = select(User).options(selectinload(User.orders))

    # Filter
    if search:
        stmt = stmt.where(User.name.contains(search) | User.email.contains(search))

    # Count (for pagination)
    count_stmt = select(func.count()).select_from(stmt.subquery())
    total = (await db.execute(count_stmt)).scalar()

    # Paginate
    stmt = stmt.order_by(User.created_at.desc())
    stmt = stmt.offset((page - 1) * page_size).limit(page_size)

    result = await db.execute(stmt)
    users = list(result.scalars().all())

    return users, total
```

> **See also**: `database-patterns` — Connection pooling, N+1 prevention, Alembic migrations, indexing strategies.

---

### 4. Alembic

### Migration Patterns

```python
# alembic/versions/001_create_users_table.py
"""create users table

Revision ID: 001
Revises:
Create Date: 2026-05-14
"""
from alembic import op
import sqlalchemy as sa

revision = "001"
down_revision = None
branch_labels = None
depends_on = None

def upgrade():
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("email", sa.String(255), nullable=False),
        sa.Column("hashed_password", sa.String(255), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now(),
                  onupdate=sa.func.now()),
    )
    # Unique enforcement lives in ONE place: this unique index — matches the
    # model's `mapped_column(String(255), unique=True, index=True)`
    op.create_index("ix_users_email", "users", ["email"], unique=True)

def downgrade():
    op.drop_index("ix_users_email", table_name="users")
    op.drop_table("users")
```

> **See also**: `database-patterns` — Connection pooling, N+1 prevention, Alembic migrations, indexing strategies.

### Best Practices

```bash
# Create migration (auto-generate)
alembic revision --autogenerate -m "create users table"

# Run migrations
alembic upgrade head

# Rollback one migration
alembic downgrade -1

# Rollback to specific migration
alembic downgrade 001

# Multi-DB? No — separate DBs, separate Alembic configs
```

---

### 5. Jinja2

### Template Inheritance

```html
{# templates/base.html #}
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{% block title %}MyApp{% endblock %}</title>
</head>
<body>
    <nav>
        {% if current_user %}
            <a href="/profile">{{ current_user.name }}</a>
            <a href="/logout">Logout</a>
        {% else %}
            <a href="/login">Login</a>
        {% endif %}
    </nav>

    <main>
        {% block content %}{% endblock %}
    </main>

    {% block scripts %}{% endblock %}
</body>
</html>
```

```html
{# templates/user_list.html #}
{% extends "base.html" %}

{% block title %}Users{% endblock %}

{% block content %}
<h1>Users</h1>

{% if users %}
    <table>
        {% for user in users %}
        <tr>
            <td>{{ user.name }}</td>
            <td>{{ user.email }}</td>
            <td>
                <a href="/users/{{ user.id }}">View</a>
                {% if current_user.role == "admin" %}
                    <a href="/users/{{ user.id }}/delete">Delete</a>
                {% endif %}
            </td>
        </tr>
        {% endfor %}
    </table>
{% else %}
    <p>No users found.</p>
{% endif %}
{% endblock %}
```

### Custom Filters

```python
from jinja2 import Environment, FileSystemLoader, select_autoescape

def datetimeformat(value, format='%Y-%m-%d %H:%M'):
    """Format datetime in templates."""
    return value.strftime(format)

def truncate_words(value, count=50):
    """Truncate text to N words."""
    words = value.split()
    if len(words) > count:
        return " ".join(words[:count]) + "..."
    return value

env = Environment(
    loader=FileSystemLoader("templates"),
    autoescape=select_autoescape(["html", "xml"]),
)
env.filters["datetimeformat"] = datetimeformat
env.filters["truncate_words"] = truncate_words
```

> **See also**: `secure-coding-patterns` — XSS prevention through `autoescape`, output encoding, content security policies.

---

### 6. MCP (Model Context Protocol)

### MCP Server Pattern

> **API level**: for production servers prefer the high-level API — `FastMCP` (`from mcp.server.fastmcp import FastMCP`) in MCP Python SDK 1.x, renamed to `MCPServer` (`from mcp.server import MCPServer`) in SDK 2.x. It derives input schemas from type hints and converts a raised `ToolError` into a structured error result. The **low-level** `Server` example below (1.x decorator style) is kept to show the protocol layer explicitly.

```python
# mcp_server.py — Model Context Protocol server (LOW-LEVEL API)
import json

import httpx
from mcp.server.lowlevel import Server
from mcp.types import CallToolResult, Resource, TextContent, Tool

# Server instance
server = Server("weather-mcp-server")

# ONE helper shared by resource and tool handlers
DEFAULT_LOCATION = "Moscow"

async def fetch_weather(location: str, units: str = "metric") -> dict:
    """Fetch current weather from the external API."""
    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.get(
            "https://api.weather.example/v1/current",
            params={"q": location, "units": units},
        )
        resp.raise_for_status()
        return resp.json()

# Resources — data access
@server.list_resources()
async def list_resources():
    return [
        Resource(
            uri="weather://current",
            name="Current Weather",
            description="Real-time weather for configured location",
            mimeType="application/json"
        )
    ]

@server.read_resource()
async def read_resource(uri):
    if uri == "weather://current":
        weather = await fetch_weather(DEFAULT_LOCATION)
        return json.dumps(weather)
    # Raising for an unknown resource is correct — it surfaces as a
    # protocol-level (JSON-RPC) error. Tools return structured errors instead.
    raise ValueError(f"Unknown resource: {uri}")

# Tools — actions
@server.list_tools()
async def list_tools():
    return [
        Tool(
            name="get_weather",
            description="Get current weather for a location",
            inputSchema={
                "type": "object",
                "properties": {
                    "location": {
                        "type": "string",
                        "description": "City name or coordinates"
                    },
                    "units": {
                        "type": "string",
                        "enum": ["metric", "imperial"],
                        "default": "metric"
                    }
                },
                "required": ["location"]
            }
        )
    ]

@server.call_tool()
async def call_tool(name: str, arguments: dict) -> CallToolResult:
    if name != "get_weather":
        # Structured error result the model can read — don't raise raw
        # exceptions from tool handlers (they surface as opaque protocol errors)
        return CallToolResult(
            content=[TextContent(type="text", text=f"Unknown tool: {name}")],
            isError=True,
        )
    try:
        weather = await fetch_weather(
            arguments["location"], arguments.get("units", "metric")
        )
    except httpx.HTTPError as exc:
        return CallToolResult(
            content=[TextContent(type="text", text=f"Weather lookup failed: {exc}")],
            isError=True,
        )
    return CallToolResult(
        content=[TextContent(type="text", text=json.dumps(weather, indent=2))]
    )
```

### MCP Client Pattern

```python
# client.py — MCP client
# ClientSession is re-exported at the top level (`from mcp import ClientSession`);
# the module path is `mcp.client.session` — `from mcp.client import ClientSession`
# is NOT valid.
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

async def main():
    server_params = StdioServerParameters(command="python", args=["mcp_server.py"])
    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            # Initialize
            await session.initialize()

            # List available tools
            tools = await session.list_tools()

            # Call a tool
            result = await session.call_tool("get_weather", {
                "location": "Moscow",
                "units": "metric"
            })
            print(result)
```

### Best Practices

- **Single responsibility** — one server = one domain area
- **Descriptive names** — `get_weather` not `gw`
- **Rich descriptions** — describe what each tool does
- **Input schemas** — validate at the protocol level
- **Error handling** — tool failures return structured error results (`isError=True`) the model can read; raising is for protocol-level errors (e.g. unknown resource)
- **Transport** — stdio for CLI, HTTP for web

---

### Pydantic v2 Deep Dive
```python
from pydantic import BaseModel, ConfigDict, field_validator, model_validator, field_serializer
from datetime import datetime
from typing import Self

class UserCreate(BaseModel):
    model_config = ConfigDict(
        str_strip_whitespace=True,
        str_min_length=1,
        extra="forbid",  # reject unknown fields
    )

    email: str
    name: str
    age: int | None = None
    tags: list[str] = []

    @field_validator("email")
    @classmethod
    def validate_email(cls, v: str) -> str:
        if "@" not in v or "." not in v.split("@")[1]:
            raise ValueError("Invalid email format")
        return v.lower()

    @model_validator(mode="after")
    def validate_age(self) -> Self:
        if self.age is not None and self.age < 0:
            raise ValueError("Age cannot be negative")
        return self

    @field_serializer("tags")
    def serialize_tags(self, tags: list[str]) -> list[str]:
        return sorted(set(t.lower() for t in tags))
```

> **See also**: `observability-patterns` — Structured logging with structlog, request correlation, OpenTelemetry.

> **See also**: `performance-optimization` — Structured concurrency with TaskGroup, async optimization patterns.

### Protocol and TypedDict
```python
from typing import NotRequired, Protocol, TypedDict, runtime_checkable

# Protocol — structural subtyping (duck typing with type safety)
@runtime_checkable
class Repository(Protocol):
    async def find_by_id(self, id: int) -> dict: ...
    async def create(self, data: dict) -> dict: ...
    async def delete(self, id: int) -> None: ...

# Any class with these methods satisfies Repository — no inheritance needed
class PostgresUserRepo:
    async def find_by_id(self, id: int) -> dict:
        return await self.pool.fetchrow("SELECT * FROM users WHERE id=$1", id)
    async def create(self, data: dict) -> dict:
        # asyncpg takes POSITIONAL args for $n placeholders — no **kwargs
        return await self.pool.fetchrow(
            "INSERT INTO users(name, email) VALUES($1, $2) RETURNING *",
            data["name"],
            data["email"],
        )
    async def delete(self, id: int) -> None:
        await self.pool.execute("DELETE FROM users WHERE id=$1", id)

def process(repo: Repository):  # Accepts any conforming implementation
    ...

# TypedDict — typed dictionaries (for JSON schemas, configs)
class APIError(TypedDict):
    code: str
    message: str
    details: dict[str, list[str]]

# Optional keys — PEP 655 idiom (Python 3.11+): NotRequired[]/Required[] mark
# keys individually, instead of total=False making EVERY key optional.
# (Alternative idiom: two TypedDicts with inheritance — a total=False base
# holding optional keys, and a derived default-total dict of required ones.)
class UserResponse(TypedDict):
    id: int                       # required (default)
    email: str                    # required
    name: str                     # required
    avatar_url: NotRequired[str]  # optional
```

## Best Practices

1. **Type hints everywhere** — `mypy --strict` for critical code
2. **Use SQLAlchemy 2.0 style** — `select()` not `session.query()`
3. **FastAPI dependency injection** — do not use global objects
4. **Alembic for all migrations** — never change schema manually
5. **Jinja2 autoescape** — always `select_autoescape()`
6. **pydantic-settings** — env vars, no hardcoding
7. **Async all the way** — do not mix sync and async
8. **Project structure** — src layout, not flat layout
9. **Logging** — structured logging via `observability-patterns`, not print()
10. **Testing** — pytest fixtures, not unittest classes

## Common Pitfalls

| Mistake | Why It's Bad | Fix |
|---|---|---|
| `session.query()` style | Old 1.x API — deprecated | `select()` 2.0 style |
| Sync functions in async | Blocks event loop | Async versions: asyncpg, httpx, aiosqlite |
| `from pydantic import BaseSettings` | Deprecated in v2 | `from pydantic_settings import BaseSettings` |
| Flat layout (`myapp/`, `tests/`) | Import conflicts | src layout (`src/myapp/`) |
| Hardcoded config | Environment-dependent | pydantic-settings + env file |
| No `expire_on_commit=False` | ORM objects detached after commit | Session `expire_on_commit=False` |
| `session.query().all()` for large tables | OOM | Paginate, yield batches |
| Auto-migrate in production | Dangerous | Manual review, `alembic upgrade head` |
| Jinja2 without autoescape | XSS risk | `autoescape=select_autoescape()` |
| MCP without inputSchema | Bad agent experience | Always define schema |

## Context7 Integration

When Context7 MCP tools are available in your session, use them to fetch up-to-date library documentation instead of relying on memory. Tool names vary by installation (e.g. `mcp__context7__resolve-library-id` / `mcp__context7__query-docs`, or plugin-prefixed variants such as `mcp__plugin_context7_context7__*`) — check the available-tools listing for the exact names. Always resolve the library ID first; the IDs in the table below are examples and may change.

| Library | Context7 ID | When to Query |
|---------|-------------|---------------|
| Python | (query "Python 3.13") | Language features, stdlib updates |
| FastAPI | `/websites/fastapi_tiangolo` | Dependencies, middleware, routing |
| SQLAlchemy | `/websites/sqlalchemy_en_20` | ORM patterns, session config |
| Alembic | `/websites/alembic_sqlalchemy` | Migration patterns |
| Pydantic | `/pydantic/pydantic` | Validation, model config |
