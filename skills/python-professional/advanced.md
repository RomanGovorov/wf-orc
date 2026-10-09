# Advanced Patterns: Python Professional

> This file extends [`SKILL.md`](SKILL.md) with advanced patterns and edge cases.

## Pydantic v2 Deep Dive

### Advanced Validation

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

### Key Features

- **`ConfigDict`** — centralized model configuration
- **`field_validator`** — per-field validation with `@classmethod`
- **`model_validator`** — cross-field validation with `mode="after"`
- **`field_serializer`** — custom serialization logic
- **`extra="forbid"`** — reject unknown fields (strict mode)

## Protocol and TypedDict

### Protocol — Structural Subtyping

```python
from typing import Protocol, runtime_checkable

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
        # asyncpg takes POSITIONAL args for $n placeholders
        return await self.pool.fetchrow(
            "INSERT INTO users(name, email) VALUES($1, $2) RETURNING *",
            data["name"],
            data["email"],
        )
    
    async def delete(self, id: int) -> None:
        await self.pool.execute("DELETE FROM users WHERE id=$1", id)

def process(repo: Repository):  # Accepts any conforming implementation
    ...
```

### TypedDict — Typed Dictionaries

```python
from typing import NotRequired, TypedDict

class APIError(TypedDict):
    code: str
    message: str
    details: dict[str, list[str]]

# Optional keys — PEP 655 idiom (Python 3.11+)
class UserResponse(TypedDict):
    id: int                       # required (default)
    email: str                    # required
    name: str                     # required
    avatar_url: NotRequired[str]  # optional
```

**When to use:**
- **Protocol** — duck typing with type safety, interface definitions
- **TypedDict** — JSON schemas, API responses, configs with mixed required/optional keys

## Advanced FastAPI Patterns

### Background Tasks — Critical Pattern

```python
from fastapi import BackgroundTasks
from pydantic import BaseModel, ConfigDict

class UserRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    email: str
    name: str

async def send_welcome_email(email: str):
    """Background task — receives plain string, NOT User ORM object.
    
    CRITICAL: Background tasks run after the request's DB session closes.
    Passing an ORM object raises DetachedInstanceError on lazy access.
    Always pass plain values (user.id, user.email).
    """
    await email_service.send(email, "Welcome!", template="welcome")

@router.post("/users", response_model=UserRead)
async def create_user(
    data: UserCreate,
    background_tasks: BackgroundTasks,
    db = Depends(get_db),
):
    user = await user_service.create(db, data)
    # Pass plain values — session closes before background task runs
    background_tasks.add_task(send_welcome_email, user.email)
    return user
```

### Middleware Pattern

```python
from fastapi import Request
import time

@app.middleware("http")
async def add_timing_header(request: Request, call_next):
    start = time.perf_counter()
    response = await call_next(request)
    response.headers["X-Response-Time"] = f"{time.perf_counter() - start:.3f}s"
    return response
```

### Role-Based Authorization

```python
async def require_admin(
    current_user: User = Depends(get_current_user),
) -> User:
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin role required")
    return current_user

@router.delete("/users/{user_id}")
async def delete_user(
    user_id: int,
    db = Depends(get_db),
    admin = Depends(require_admin),
):
    ...
```

## Advanced SQLAlchemy Patterns

### Relationship Configuration

```python
class User(Base, TimestampMixin):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100))
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    
    # One-to-many with cascade
    orders: Mapped[list["Order"]] = relationship(
        "Order",
        back_populates="user",
        cascade="all, delete-orphan"
    )
    
    # One-to-one
    profile: Mapped["UserProfile" | None] = relationship(
        "UserProfile",
        back_populates="user",
        uselist=False
    )
```

### Eager Loading Strategies

```python
from sqlalchemy.orm import selectinload, joinedload

# selectinload — best for collections, multiple queries
stmt = select(User).options(selectinload(User.orders))

# joinedload — best for single related objects, single query
stmt = select(User).options(joinedload(User.profile))
```

**When to use:**
- **selectinload** — one-to-many, many-to-many (avoids Cartesian products)
- **joinedload** — many-to-one, one-to-one (single object)

## Advanced Jinja2 Patterns

### Custom Filters

```python
from jinja2 import Environment, FileSystemLoader, select_autoescape

def datetimeformat(value, format='%Y-%m-%d %H:%M'):
    return value.strftime(format)

def truncate_words(value, count=50):
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

### Usage in Templates

```html
<p>{{ user.created_at | datetimeformat('%d %b %Y') }}</p>
<p>{{ article.content | truncate_words(100) }}</p>
```

## Advanced MCP Patterns

### High-Level API (Production)

```python
# For production servers prefer FastMCP/MCPServer
from mcp.server.fastmcp import FastMCP  # SDK 1.x
# or
from mcp.server import MCPServer  # SDK 2.x

mcp = FastMCP("weather-server")

@mcp.tool()
async def get_weather(location: str, units: str = "metric") -> dict:
    """Get current weather for a location."""
    # Implementation — schemas derived from type hints automatically
    ...
```

### Error Handling Strategy

```python
@server.call_tool()
async def call_tool(name: str, arguments: dict) -> CallToolResult:
    try:
        result = await fetch_data(arguments["location"])
        return CallToolResult(
            content=[TextContent(type="text", text=json.dumps(result))]
        )
    except httpx.HTTPError as exc:
        # Structured error result the model can read
        return CallToolResult(
            content=[TextContent(type="text", text=f"Request failed: {exc}")],
            isError=True,
        )
    except ValueError as exc:
        # Protocol-level error — raise for unknown resources
        raise
```

**Rule:** Tool failures → structured error results. Protocol errors → raise exceptions.

## Performance Considerations

### Async Best Practices

```python
# ✅ GOOD — async all the way
async def get_users():
    async with httpx.AsyncClient() as client:
        return await client.get("/api/users")

# ❌ BAD — blocks event loop
def get_users():
    return requests.get("/api/users")  # sync!
```

### Database Session Management

```python
# ✅ GOOD — commit on success, rollback on exception
async def get_db():
    async with async_session() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise

# ❌ BAD — never commits
async def get_db():
    async with async_session() as session:
        yield session  # who commits?
```

## Edge Cases

### Type Checking with asyncpg

```python
# asyncpg requires bind type to match column type
async def get_user(db: AsyncSession, user_id: str):
    # ❌ WRONG — user_id is str, but User.id is int
    user = await db.get(User, user_id)  # InterfaceError on asyncpg
    
    # ✅ CORRECT — convert first
    user = await db.get(User, int(user_id))
```

### Pydantic Settings Import

```python
# ❌ WRONG — deprecated in Pydantic v2
from pydantic import BaseSettings

# ✅ CORRECT — separate package
from pydantic_settings import BaseSettings
```

### DetachedInstanceError Prevention

```python
# ❌ WRONG — passing ORM object to background task
background_tasks.add_task(send_email, user)  # DetachedInstanceError!

# ✅ CORRECT — pass plain values
background_tasks.add_task(send_email, user.email)
```

## Migration Strategies

### From SQLAlchemy 1.x to 2.0

```python
# ❌ OLD — 1.x style
users = session.query(User).filter(User.active == True).all()

# ✅ NEW — 2.0 style
stmt = select(User).where(User.active == True)
users = (await db.execute(stmt)).scalars().all()
```

### From Flask to FastAPI

```python
# Flask
@app.route("/users/<int:user_id>")
def get_user(user_id):
    return jsonify({"id": user_id})

# FastAPI
@router.get("/users/{user_id}")
async def get_user(user_id: int):
    return {"id": user_id}
```

## Troubleshooting

### Common Errors

| Error | Cause | Solution |
|-------|-------|----------|
| `DetachedInstanceError` | Accessing ORM object after session closes | Pass plain values, not ORM objects |
| `InterfaceError` (asyncpg) | Type mismatch in bind parameters | Convert types before query |
| `ImportError: BaseSettings` | Pydantic v2 breaking change | Use `pydantic_settings` package |
| `Event loop is closed` | Async/sync mixing | Use async versions of libraries |
| `TemplateNotFound` | Jinja2 loader misconfiguration | Check `FileSystemLoader` path |

## Additional Resources

- **Core patterns:** See [`SKILL.md`](SKILL.md) for essential patterns
- **Code examples:** See [`examples.md`](examples.md) for complete working examples
