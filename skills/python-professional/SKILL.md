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

#### Project Structure

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
│       ├── core/
│       │   ├── security.py
│       │   └── db.py
│       ├── models/
│       ├── schemas/
│       ├── services/
│       └── templates/
├── tests/
│   ├── conftest.py
│   ├── test_api/
│   ├── test_services/
│   └── integration/
└── scripts/
```

#### Type Hints

```python
from typing import Any

# ✅ GOOD
def get_user(user_id: int) -> User | None: ...
def process(data: list[str]) -> dict[str, Any]: ...

# Python 3.12+ type alias
type UserId = int
type JsonDict = dict[str, Any]
```

#### Naming Conventions

```python
# Classes — PascalCase
class UserRepository: ...

# Functions/variables — snake_case
def get_user_by_email(email: str): ...

# Constants — UPPER_SNAKE_CASE
MAX_RETRY = 3
DEFAULT_PAGE_SIZE = 20

# Private — leading underscore
def _internal_helper(): ...
```

### 2. FastAPI

#### Application Factory

```python
# src/myapp/main.py
from contextlib import asynccontextmanager
from fastapi import FastAPI
from myapp.core.db import db_engine

@asynccontextmanager
async def lifespan(app: FastAPI):
    async with db_engine.connect():
        pass
    yield
    await db_engine.dispose()

def create_app() -> FastAPI:
    app = FastAPI(title="MyApp", lifespan=lifespan)
    from .api.router import router
    app.include_router(router)
    return app

app = create_app()
```

#### Dependency Injection

```python
# src/myapp/api/deps.py
from fastapi import Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

async def get_db():
    async with async_session() as session:
        yield session

async def get_current_user(
    db: AsyncSession = Depends(get_db),
    token: str = Depends(oauth2_scheme),
) -> User:
    payload = verify_token(token)
    user_id = int(payload["sub"])
    user = await db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=401)
    return user
```

> **See also**: `api-design-principles` — REST/GraphQL patterns, pagination, versioning. `secure-coding-patterns` — JWT auth, CSRF, input validation.

### 3. SQLAlchemy 2.0

#### Modern Model Definition

```python
# src/myapp/models/base.py
from sqlalchemy.orm import DeclarativeBase, mapped_column, Mapped
from sqlalchemy import DateTime, func
from datetime import datetime

class Base(DeclarativeBase):
    pass

class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )
```

#### Modern Query Patterns

```python
from sqlalchemy import select, func
from sqlalchemy.orm import selectinload

async def get_users(
    db: AsyncSession,
    page: int = 1,
    page_size: int = 20,
) -> tuple[list[User], int]:
    stmt = select(User).options(selectinload(User.orders))
    count_stmt = select(func.count()).select_from(stmt.subquery())
    total = (await db.execute(count_stmt)).scalar()
    
    stmt = stmt.order_by(User.created_at.desc())
    stmt = stmt.offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(stmt)
    return list(result.scalars().all()), total
```

> **See also**: `database-patterns` — Connection pooling, N+1 prevention, indexing strategies.

### 4. Alembic

#### Migration Pattern

```python
# alembic/versions/001_create_users_table.py
from alembic import op
import sqlalchemy as sa

def upgrade():
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("email", sa.String(255), nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
    )
    op.create_index("ix_users_email", "users", ["email"], unique=True)

def downgrade():
    op.drop_index("ix_users_email", table_name="users")
    op.drop_table("users")
```

```bash
# Create migration
alembic revision --autogenerate -m "create users table"

# Run migrations
alembic upgrade head
```

### 5. Jinja2

#### Template Inheritance

```html
{# templates/base.html #}
<!DOCTYPE html>
<html lang="en">
<head>
    <title>{% block title %}MyApp{% endblock %}</title>
</head>
<body>
    <nav>
        {% if current_user %}
            <a href="/profile">{{ current_user.name }}</a>
        {% endif %}
    </nav>
    <main>{% block content %}{% endblock %}</main>
</body>
</html>
```

```html
{# templates/user_list.html #}
{% extends "base.html" %}
{% block content %}
<h1>Users</h1>
{% for user in users %}
    <p>{{ user.name }}</p>
{% endfor %}
{% endblock %}
```

> **See also**: `secure-coding-patterns` — XSS prevention through `autoescape`.

### 6. MCP (Model Context Protocol)

#### MCP Server Pattern

```python
# mcp_server.py
from mcp.server.lowlevel import Server
from mcp.types import CallToolResult, TextContent, Tool

server = Server("weather-mcp-server")

@server.list_tools()
async def list_tools():
    return [Tool(
        name="get_weather",
        description="Get current weather",
        inputSchema={"type": "object", "properties": {"location": {"type": "string"}}}
    )]

@server.call_tool()
async def call_tool(name: str, arguments: dict) -> CallToolResult:
    if name != "get_weather":
        return CallToolResult(
            content=[TextContent(type="text", text=f"Unknown tool: {name}")],
            isError=True,
        )
    # ... implementation
```

#### Best Practices

- **Single responsibility** — one server = one domain area
- **Descriptive names** — `get_weather` not `gw`
- **Input schemas** — validate at the protocol level
- **Error handling** — tool failures return structured error results (`isError=True`)

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
| Sync functions in async | Blocks event loop | Async versions: asyncpg, httpx |
| `from pydantic import BaseSettings` | Deprecated in v2 | `from pydantic_settings import BaseSettings` |
| Flat layout | Import conflicts | src layout (`src/myapp/`) |
| Hardcoded config | Environment-dependent | pydantic-settings + env file |
| No `expire_on_commit=False` | ORM objects detached | Session `expire_on_commit=False` |
| Jinja2 without autoescape | XSS risk | `autoescape=select_autoescape()` |
| MCP without inputSchema | Bad agent experience | Always define schema |

## Context7 Integration

When Context7 MCP tools are available, use them to fetch up-to-date library documentation.

| Library | Context7 ID | When to Query |
|---------|-------------|---------------|
| Python | (query "Python 3.13") | Language features, stdlib updates |
| FastAPI | `/websites/fastapi_tiangolo` | Dependencies, middleware, routing |
| SQLAlchemy | `/websites/sqlalchemy_en_20` | ORM patterns, session config |
| Alembic | `/websites/alembic_sqlalchemy` | Migration patterns |
| Pydantic | `/pydantic/pydantic` | Validation, model config |

## Additional Resources

- **Advanced patterns:** See [`advanced.md`](advanced.md) for deep dives, edge cases, and advanced techniques
- **Code examples:** See [`examples.md`](examples.md) for complete working examples and templates
