# Code Examples: Python Professional

> Working examples for [`SKILL.md`](SKILL.md).

## Example 1: Complete FastAPI Application

### Project Structure

```
myapp/
├── pyproject.toml
├── src/myapp/
│   ├── __init__.py
│   ├── main.py
│   ├── config.py
│   ├── api/
│   │   ├── router.py
│   │   ├── deps.py
│   │   └── v1/endpoints/users.py
│   ├── core/
│   │   ├── db.py
│   │   └── security.py
│   ├── models/
│   │   ├── base.py
│   │   └── user.py
│   └── schemas/
│       └── user.py
└── tests/
    └── conftest.py
```

### Configuration

```python
# src/myapp/config.py
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    app_name: str = "MyApp"
    debug: bool = False
    database_url: str
    secret_key: str
    
    class Config:
        env_file = ".env"

settings = Settings()
```

### Database Setup

```python
# src/myapp/core/db.py
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from myapp.config import settings

engine = create_async_engine(settings.database_url, echo=settings.debug)
async_session = async_sessionmaker(engine, expire_on_commit=False)
```

### Models

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

```python
# src/myapp/models/user.py
from sqlalchemy import String, Boolean
from sqlalchemy.orm import mapped_column, Mapped
from .base import Base, TimestampMixin

class User(Base, TimestampMixin):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100))
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    hashed_password: Mapped[str] = mapped_column(String(255))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
```

### Schemas

```python
# src/myapp/schemas/user.py
from pydantic import BaseModel, ConfigDict, field_validator

class UserCreate(BaseModel):
    email: str
    name: str
    password: str

    @field_validator("email")
    @classmethod
    def validate_email(cls, v: str) -> str:
        if "@" not in v:
            raise ValueError("Invalid email")
        return v.lower()

class UserRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    
    id: int
    email: str
    name: str
    is_active: bool
```

### Dependencies

```python
# src/myapp/api/deps.py
from fastapi import Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from myapp.core.db import async_session
from myapp.models.user import User

async def get_db():
    async with async_session() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise

async def get_current_user(
    db: AsyncSession = Depends(get_db),
    token: str = Depends(oauth2_scheme),
) -> User:
    payload = verify_token(token)
    user = await db.get(User, int(payload["sub"]))
    if not user:
        raise HTTPException(status_code=401, detail="Invalid user")
    return user
```

### Endpoints

```python
# src/myapp/api/v1/endpoints/users.py
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from myapp.api.deps import get_db, get_current_user
from myapp.models.user import User
from myapp.schemas.user import UserCreate, UserRead

router = APIRouter(prefix="/users", tags=["users"])

@router.get("/me", response_model=UserRead)
async def read_current_user(current_user: User = Depends(get_current_user)):
    return current_user

@router.get("/{user_id}", response_model=UserRead)
async def read_user(user_id: int, db: AsyncSession = Depends(get_db)):
    user = await db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user

@router.post("/", response_model=UserRead, status_code=201)
async def create_user(data: UserCreate, db: AsyncSession = Depends(get_db)):
    # Check if exists
    stmt = select(User).where(User.email == data.email)
    existing = (await db.execute(stmt)).scalar_one_or_none()
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    # Create
    user = User(
        email=data.email,
        name=data.name,
        hashed_password=hash_password(data.password),
    )
    db.add(user)
    await db.flush()
    await db.refresh(user)
    return user
```

### Application Factory

```python
# src/myapp/main.py
from contextlib import asynccontextmanager
from fastapi import FastAPI
from myapp.core.db import engine
from myapp.api.router import api_router

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    async with engine.connect():
        pass
    yield
    # Shutdown
    await engine.dispose()

def create_app() -> FastAPI:
    app = FastAPI(title="MyApp", lifespan=lifespan)
    app.include_router(api_router, prefix="/api/v1")
    return app

app = create_app()
```

## Example 2: Complete Alembic Migration

### Migration File

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
    op.create_index("ix_users_email", "users", ["email"], unique=True)

def downgrade():
    op.drop_index("ix_users_email", table_name="users")
    op.drop_table("users")
```

### Commands

```bash
# Initialize Alembic
alembic init alembic

# Create migration
alembic revision --autogenerate -m "create users table"

# Apply migrations
alembic upgrade head

# Rollback one step
alembic downgrade -1

# Show current revision
alembic current

# Show migration history
alembic history
```

## Example 3: Complete Jinja2 Templates

### Base Template

```html
{# templates/base.html #}
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{% block title %}MyApp{% endblock %}</title>
    <link rel="stylesheet" href="/static/css/style.css">
</head>
<body>
    <nav>
        {% if current_user %}
            <a href="/profile">{{ current_user.name }}</a>
            <a href="/logout">Logout</a>
        {% else %}
            <a href="/login">Login</a>
            <a href="/register">Register</a>
        {% endif %}
    </nav>

    <main>
        {% with messages = get_flashed_messages() %}
            {% if messages %}
                <ul class="flashes">
                {% for message in messages %}
                    <li>{{ message }}</li>
                {% endfor %}
                </ul>
            {% endif %}
        {% endwith %}
        
        {% block content %}{% endblock %}
    </main>

    <footer>
        <p>&copy; 2026 MyApp</p>
    </footer>

    {% block scripts %}{% endblock %}
</body>
</html>
```

### List Template

```html
{# templates/user_list.html #}
{% extends "base.html" %}

{% block title %}Users{% endblock %}

{% block content %}
<h1>Users</h1>

{% if users %}
    <table>
        <thead>
            <tr>
                <th>Name</th>
                <th>Email</th>
                <th>Actions</th>
            </tr>
        </thead>
        <tbody>
            {% for user in users %}
            <tr>
                <td>{{ user.name }}</td>
                <td>{{ user.email }}</td>
                <td>
                    <a href="/users/{{ user.id }}">View</a>
                    {% if current_user.role == "admin" %}
                        | <a href="/users/{{ user.id }}/delete">Delete</a>
                    {% endif %}
                </td>
            </tr>
            {% endfor %}
        </tbody>
    </table>
{% else %}
    <p>No users found.</p>
{% endif %}
{% endblock %}
```

### Detail Template

```html
{# templates/user_detail.html #}
{% extends "base.html" %}

{% block title %}{{ user.name }}{% endblock %}

{% block content %}
<h1>{{ user.name }}</h1>
<p>Email: {{ user.email }}</p>
<p>Joined: {{ user.created_at | datetimeformat('%d %b %Y') }}</p>

{% if user.bio %}
    <div class="bio">
        <h2>Bio</h2>
        <p>{{ user.bio }}</p>
    </div>
{% endif %}

<a href="/users">Back to list</a>
{% endblock %}
```

## Example 4: Complete MCP Server

### Low-Level API

```python
# mcp_server.py
import json
import httpx
from mcp.server.lowlevel import Server
from mcp.types import CallToolResult, Resource, TextContent, Tool

server = Server("weather-mcp-server")

DEFAULT_LOCATION = "Moscow"

async def fetch_weather(location: str, units: str = "metric") -> dict:
    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.get(
            "https://api.weather.example/v1/current",
            params={"q": location, "units": units},
        )
        resp.raise_for_status()
        return resp.json()

@server.list_resources()
async def list_resources():
    return [
        Resource(
            uri="weather://current",
            name="Current Weather",
            description="Real-time weather data",
            mimeType="application/json"
        )
    ]

@server.read_resource()
async def read_resource(uri):
    if uri == "weather://current":
        weather = await fetch_weather(DEFAULT_LOCATION)
        return json.dumps(weather)
    raise ValueError(f"Unknown resource: {uri}")

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
        return CallToolResult(
            content=[TextContent(type="text", text=f"Unknown tool: {name}")],
            isError=True,
        )
    try:
        weather = await fetch_weather(
            arguments["location"],
            arguments.get("units", "metric")
        )
        return CallToolResult(
            content=[TextContent(type="text", text=json.dumps(weather, indent=2))]
        )
    except httpx.HTTPError as exc:
        return CallToolResult(
            content=[TextContent(type="text", text=f"Weather lookup failed: {exc}")],
            isError=True,
        )
```

### High-Level API (Production)

```python
# mcp_server_fast.py
from mcp.server.fastmcp import FastMCP
import httpx

mcp = FastMCP("weather-server")

@mcp.tool()
async def get_weather(location: str, units: str = "metric") -> dict:
    """Get current weather for a location.
    
    Args:
        location: City name or coordinates
        units: Temperature units (metric/imperial)
    """
    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.get(
            "https://api.weather.example/v1/current",
            params={"q": location, "units": units},
        )
        resp.raise_for_status()
        return resp.json()

@mcp.resource("weather://current")
async def current_weather() -> dict:
    """Current weather for default location."""
    return await get_weather("Moscow")
```

## Example 5: MCP Client

```python
# client.py
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

async def main():
    server_params = StdioServerParameters(
        command="python",
        args=["mcp_server.py"]
    )
    
    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            # Initialize connection
            await session.initialize()

            # List available tools
            tools = await session.list_tools()
            print(f"Available tools: {[t.name for t in tools.tools]}")

            # Call a tool
            result = await session.call_tool(
                "get_weather",
                {"location": "Moscow", "units": "metric"}
            )
            print(f"Weather: {result.content[0].text}")

            # Read a resource
            resource = await session.read_resource("weather://current")
            print(f"Current: {resource.contents[0].text}")
```

## Example 6: Pydantic v2 Patterns

### Basic Model

```python
from pydantic import BaseModel, field_validator

class User(BaseModel):
    email: str
    name: str
    age: int | None = None

    @field_validator("email")
    @classmethod
    def validate_email(cls, v: str) -> str:
        if "@" not in v:
            raise ValueError("Invalid email")
        return v.lower()

# Usage
user = User(email="TEST@EXAMPLE.COM", name="John")
print(user.email)  # test@example.com
```

### Advanced Configuration

```python
from pydantic import BaseModel, ConfigDict, field_serializer

class Product(BaseModel):
    model_config = ConfigDict(
        str_strip_whitespace=True,
        extra="forbid",
        validate_assignment=True,
    )
    
    name: str
    tags: list[str] = []
    price: float

    @field_serializer("price")
    def format_price(self, price: float) -> str:
        return f"${price:.2f}"

# Usage
product = Product(name="  Widget  ", tags=["SALE", "new"], price=19.99)
print(product.name)  # "Widget"
print(product.model_dump())  # {'name': 'Widget', 'tags': ['SALE', 'new'], 'price': '$19.99'}
```

## Additional Resources

- **Core patterns:** See [`SKILL.md`](SKILL.md) for essential patterns
- **Advanced techniques:** See [`advanced.md`](advanced.md) for deep dives and edge cases
