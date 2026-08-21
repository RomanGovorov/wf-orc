---
name: secure-coding-patterns
description: OWASP Top-10 protection patterns, input validation, authentication, secrets management. Use when working with external data, authentication, user input processing.
priority: 10
paths:
  - "**/auth*"
  - "**/security*"
  - "**/middleware*"
  - "**/csrf*"
  - "**/encrypt*"
  - "**/secrets*"
  - "**/validation*"
  - "**/input_validation*"
  - "**/sanitize*"
---

# Secure Coding Patterns

Security pattern against common vulnerabilities. Apply when working with user input, authentication, data storage, and inter-service communication.

## When to Use This Skill

- When processing any user input (forms, APIs, files)
- When implementing authentication and authorization
- When working with databases (SQL ORM, raw queries)
- When doing inter-service communication (HTTP, gRPC, queues)
- When managing secrets and configuration
- When reviewing code for vulnerabilities
- Before deploying to production

## Core Concepts

### 1. Defense in Depth

Do not rely on a single layer of defense. Each component of the system must validate its inputs:

- **Input validation** at system boundaries (API gateway, controllers)
- **Business validation** at the service level
- **Output encoding** before sending to the client
- **Least privilege** — minimum permissions for each component

### 2. Zero Trust Architecture

Trust no one — verify every request:

- Authenticate all incoming requests
- Authorize every action
- Validate all inputs
- Log all suspicious events

### 3. Secure Defaults

Safe settings by default:

- HTTPS is mandatory
- CORS restricted
- Rate limiting by default
- Automatic logout on inactivity

## Patterns

### Pattern 1: SQL Injection Prevention (Python)

```python
# ❌ BAD: String formatting / concatenation
query = f"SELECT * FROM users WHERE email = '{user_email}'"
cursor.execute(query)

# ❌ BAD: f-string with ORM
user = db.session.query(User).filter(f"email = '{user_email}'").first()

# ✅ GOOD: Parameterized queries
cursor.execute("SELECT * FROM users WHERE email = %s", (user_email,))

# ✅ GOOD: ORM with proper expressions (SQLAlchemy 2.0)
from sqlalchemy import select
stmt = select(User).where(User.email == user_email)
user = db.session.scalar(stmt)

# ✅ GOOD: ORM with raw text — still parameterized
from sqlalchemy import text
result = db.session.execute(
    text("SELECT * FROM users WHERE email = :email"),
    {"email": user_email}
)
```

### Pattern 2: XSS Prevention

```python
# ❌ BAD: Raw HTML rendering (Jinja without autoescape)
from jinja2 import Environment
env = Environment()  # no autoescape!
template = env.from_string("<div>{{ user_input }}</div>")
template.render(user_input="<script>alert('xss')</script>")

# ✅ GOOD: Jinja2 with autoescape
from jinja2 import Environment, FileSystemLoader, select_autoescape
env = Environment(
    loader=FileSystemLoader("templates"),
    autoescape=select_autoescape(["html", "xml"]),
)
template = env.get_template("page.html")

# ✅ GOOD: FastAPI — templates with Jinja2 autoescape enabled by default
from fastapi.templating import Jinja2Templates
templates = Jinja2Templates(directory="templates")  # autoescape enabled

# ✅ GOOD: Sanitize before saving
# Note: bleach is deprecated/archived since 2023. Use nh3 (Rust-based, actively maintained).
# pip install nh3
import nh3
ALLOWED_TAGS = {"p", "b", "i", "em", "strong", "a", "ul", "ol", "li"}
ALLOWED_ATTRIBUTES = {"a": {"href", "rel"}}
clean_html = nh3.clean(user_html, tags=ALLOWED_TAGS, attributes=ALLOWED_ATTRIBUTES)
```

### Pattern 3: CSRF Protection

```python
# FastAPI with CSRF protection via custom middleware
# Note: fastapi_csrf is not a standard/popular package.
# Use a well-maintained CSRF middleware or implement double-submit cookie pattern.
from fastapi import FastAPI, Request, Depends, HTTPException
from starlette.middleware.sessions import SessionMiddleware
import secrets

app = FastAPI()
# settings comes from pydantic-settings: class Settings(BaseSettings): secret_key: str = Field(..., min_length=32)
app.add_middleware(SessionMiddleware, secret_key=settings.secret_key)

# Option 1: Double-submit cookie pattern (recommended for SPAs)
# - Server sets a CSRF token cookie (SameSite=Strict, Secure, HttpOnly)
# - Client sends the token back in X-CSRF-Token header
# - Server compares cookie value with header value

# Option 2: Custom middleware approach
from starlette.middleware.base import BaseHTTPMiddleware

class CSRFMiddleware(BaseHTTPMiddleware):
    """CSRF protection via double-submit cookie pattern."""

    UNSAFE_METHODS = {"POST", "PUT", "PATCH", "DELETE"}

    async def dispatch(self, request: Request, call_next):
        if request.method in self.UNSAFE_METHODS:
            cookie_token = request.cookies.get("csrf_token")
            header_token = request.headers.get("x-csrf-token")
            if not cookie_token or cookie_token != header_token:
                raise HTTPException(status_code=403, detail="CSRF validation failed")
        response = await call_next(request)
        if "csrf_token" not in request.cookies:
            token = secrets.token_urlsafe(32)
            response.set_cookie(
                "csrf_token", token,
                httponly=True, secure=True, samesite="strict",
            )
            response.headers["x-csrf-token"] = token
        return response

app.add_middleware(CSRFMiddleware)

@app.post("/api/users")
async def create_user(request: Request, data: UserCreate):
    # CSRF validated by middleware before reaching this handler
    ...

# HTML forms — pass CSRF token
# <form method="POST">
#     <input type="hidden" name="csrf_token" value="{{ csrf_token() }}">
# </form>
```

### Pattern 4: Secure JWT Authentication

```python
import jwt
from datetime import datetime, timedelta, timezone

SECRET_KEY = settings.secret_key  # NEVER hardcode
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

def create_access_token(data: dict) -> str:
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(
        minutes=ACCESS_TOKEN_EXPIRE_MINUTES
    )
    to_encode.update({"exp": expire, "iat": datetime.now(timezone.utc)})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

def verify_token(token: str) -> dict:
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")

# ✅ GOOD: FastAPI dependency for route protection
from fastapi import Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

security = HTTPBearer()

async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    payload = verify_token(credentials.credentials)
    user = await get_user_by_id(payload.get("sub"))
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    return user

# Protected route
@app.get("/api/me")
async def get_me(user: dict = Depends(get_current_user)):
    return user
```

### Pattern 5: Input Validation with Pydantic

```python
from pydantic import BaseModel, EmailStr, Field, field_validator, constr
import re

class UserCreate(BaseModel):
    # ✅ Type-safe constraints
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    username: constr(pattern=r"^[a-zA-Z0-9_]{3,30}$")
    age: int = Field(ge=13, le=120)

    @field_validator("password")
    @classmethod
    def password_complexity(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters")
        if not re.search(r"[A-Z]", v):
            raise ValueError("Password must contain at least one uppercase letter")
        if not re.search(r"[a-z]", v):
            raise ValueError("Password must contain at least one lowercase letter")
        if not re.search(r"\d", v):
            raise ValueError("Password must contain at least one digit")
        return v

    @field_validator("username")
    @classmethod
    def username_not_reserved(cls, v: str) -> str:
        RESERVED = {"admin", "root", "system", "api"}
        if v.lower() in RESERVED:
            raise ValueError("Username is reserved")
        return v

# FastAPI automatically validates input
@app.post("/api/users")
async def create_user(user: UserCreate):
    # user already validated — no SQL injection, no XSS via data
    ...
```

### Pattern 6: Secrets Management

```python
# ❌ BAD: Hardcoded secrets
DB_PASSWORD = "super_secret_123"
API_KEY = "sk-1234567890abcdef"

# ❌ BAD: Secrets in source code
config = {
    "database": {"password": os.environ.get("DB_PASS", "default_password")},  # default fallback!
}

# ✅ GOOD: pydantic-settings — mandatory, no defaults for secrets
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    database_url: str = Field(..., description="PostgreSQL connection string")
    secret_key: str = Field(..., min_length=32)
    jwt_algorithm: str = "HS256"  # safe default

settings = Settings()  # Raises error if required env vars missing

# ✅ GOOD: FastAPI middleware to strip sensitive response headers
from fastapi import Request, Response
import re

SENSITIVE_HEADERS = {"authorization", "x-api-key", "cookie"}

@app.middleware("http")
async def strip_sensitive_headers(request: Request, call_next):
    response = await call_next(request)
    for header in SENSITIVE_HEADERS:
        if header in response.headers:
            del response.headers[header]
    return response
```

### Pattern 7: Rate Limiting

```python
# SlowAPI — FastAPI rate limiting
from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter

from slowapi.errors import RateLimitExceeded
from fastapi.responses import JSONResponse

@app.exception_handler(RateLimitExceeded)
async def rate_limit_handler(request: Request, exc: RateLimitExceeded):
    return JSONResponse(
        status_code=429,
        content={"error": "RateLimitExceeded", "message": "Too many requests"}
    )

# Apply to routes
@app.post("/api/login")
@limiter.limit("5/minute")  # 5 attempts per minute
async def login(request: Request, credentials: LoginCredentials):
    ...  # bruteforce protection

@app.get("/api/users")
@limiter.limit("100/minute")  # general API limit
async def list_users(request: Request):
    ...
```

### Pattern 8: Security Headers (FastAPI Middleware)

```python
from starlette.middleware.base import BaseHTTPMiddleware

class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Strict-Transport-Security"] = (
            "max-age=31536000; includeSubDomains"
        )
        response.headers["Content-Security-Policy"] = "default-src 'self'"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = (
            "camera=(), microphone=(), geolocation=()"
        )
        return response

app.add_middleware(SecurityHeadersMiddleware)
```

### Pattern 9: Password Hashing (bcrypt/argon2)

```python
# Pattern 9: Password Hashing
from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["argon2", "bcrypt"], deprecated="auto")

def hash_password(password: str) -> str:
    """Hash password using argon2 (preferred) or bcrypt (fallback)."""
    return pwd_context.hash(password)

def verify_password(plain: str, hashed: str) -> bool:
    """Verify password against hash. Supports both argon2 and bcrypt."""
    return pwd_context.verify(plain, hashed)

# Registration
@app.post("/register")
async def register(data: RegisterSchema):
    if len(data.password) < 12:
        raise HTTPException(400, "Password must be at least 12 characters")
    hashed = hash_password(data.password)
    user = await create_user(data.email, hashed)
    return {"id": user.id}

# Login
@app.post("/login")
async def login(credentials: LoginSchema):
    user = await get_user_by_email(credentials.email)
    if not user or not verify_password(credentials.password, user.password_hash):
        raise HTTPException(401, "Invalid credentials")  # Generic message
    token = create_access_token(subject=user.id)
    return {"access_token": token, "token_type": "bearer"}
```

### Pattern 10: File Upload Security

```python
# Pattern 10: File Upload Security
import magic  # python-magic
from pathlib import Path

ALLOWED_MIME_TYPES = {
    "image/jpeg": [".jpg", ".jpeg"],
    "image/png": [".png"],
    "application/pdf": [".pdf"],
}
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10 MB

async def validate_upload(file: UploadFile) -> bytes:
    """Validate file upload: size, MIME type, and extension."""
    # 1. Check file size
    content = await file.read()
    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(413, f"File too large (max {MAX_FILE_SIZE // 1024 // 1024}MB)")

    # 2. Check extension
    ext = Path(file.filename).suffix.lower()
    if ext not in {e for exts in ALLOWED_MIME_TYPES.values() for e in exts}:
        raise HTTPException(415, "File type not allowed")

    # 3. Verify MIME type from content (magic bytes), not from header
    detected_mime = magic.from_buffer(content, mime=True)
    if detected_mime not in ALLOWED_MIME_TYPES:
        raise HTTPException(415, f"Invalid file content (detected: {detected_mime})")

    # 4. Check extension matches detected MIME
    if ext not in ALLOWED_MIME_TYPES.get(detected_mime, []):
        raise HTTPException(415, "File extension does not match content")

    # 5. Sanitize filename (prevent path traversal)
    safe_name = Path(file.filename).name  # strips directory components
    safe_name = "".join(c for c in safe_name if c.isalnum() or c in ".-_")

    return content, safe_name
```

### Pattern 11: SSRF Prevention

```python
# Pattern 11: SSRF Prevention
import ipaddress
from urllib.parse import urlparse
import httpx

BLOCKED_NETWORKS = [
    ipaddress.ip_network("10.0.0.0/8"),
    ipaddress.ip_network("172.16.0.0/12"),
    ipaddress.ip_network("192.168.0.0/16"),
    ipaddress.ip_network("127.0.0.0/8"),
    ipaddress.ip_network("169.254.0.0/16"),  # Link-local / cloud metadata
    ipaddress.ip_network("::1/128"),
]

async def safe_fetch(url: str, timeout: float = 5.0) -> httpx.Response:
    """Fetch URL with SSRF protection — blocks internal/private networks."""
    parsed = urlparse(url)

    # 1. Only allow http/https schemes
    if parsed.scheme not in ("http", "https"):
        raise ValueError(f"Blocked scheme: {parsed.scheme}")

    # 2. Resolve hostname to IP
    import socket
    try:
        ip_str = socket.getaddrinfo(parsed.hostname, None)[0][4][0]
        ip = ipaddress.ip_address(ip_str)
    except (socket.gaierror, ValueError):
        raise ValueError(f"Cannot resolve hostname: {parsed.hostname}")

    # 3. Block private/reserved networks
    for network in BLOCKED_NETWORKS:
        if ip in network:
            raise ValueError(f"Blocked private IP: {ip}")

    # 4. Fetch with redirect following disabled (or validate each redirect)
    async with httpx.AsyncClient(follow_redirects=False, timeout=timeout) as client:
        response = await client.get(url)
        if response.is_redirect:
            # Validate redirect target before following
            return await safe_fetch(str(response.headers["location"]), timeout)
        return response
```

### JavaScript/TypeScript Patterns

#### SQL Injection Prevention (node-postgres)
```javascript
// ❌ Vulnerable — string concatenation
const query = `SELECT * FROM users WHERE id = ${req.params.id}`;
const result = await pool.query(query);

// ✅ Safe — parameterized queries
const { rows } = await pool.query(
  'SELECT * FROM users WHERE id = $1',
  [req.params.id]
);
```

#### XSS Prevention (DOMPurify + React)
```typescript
// ❌ Vulnerable — dangerouslySetInnerHTML with untrusted data
<div dangerouslySetInnerHTML={{ __html: userInput }} />

// ✅ Safe — sanitize with DOMPurify
import DOMPurify from 'dompurify';
const clean = DOMPurify.sanitize(userInput, { ALLOWED_TAGS: ['b', 'i', 'em', 'strong', 'a'] });
<div dangerouslySetInnerHTML={{ __html: clean }} />

// ✅ Better — React auto-escapes JSX expressions
<p>{userInput}</p>
```

#### CSRF Protection (Express + csrf-csrf)
```typescript
import express from 'express';
import cookieParser from 'cookie-parser';
import { doubleCsrf } from 'csrf-csrf';

const app = express();
app.use(cookieParser());

const { generateToken, doubleCsrfProtection } = doubleCsrf({
  getSecret: () => process.env.CSRF_SECRET!,
  cookieName: '__csrf',
  cookieOptions: { sameSite: 'strict', secure: true, httpOnly: true },
  size: 64,
});

// Apply to state-changing routes
app.post('/api/transfer', doubleCsrfProtection, (req, res) => {
  // CSRF token validated by middleware
  res.json({ status: 'ok' });
});
```

> **See also**: `api-design-principles` — API validation patterns, pagination, error handling.
> **See also**: `javascript-typescript-professional` — Zod schema validation, type inference, transforms.

#### Secrets Management (Node.js)
```typescript
// Use environment variables with validation
import { z } from 'zod';

const EnvSchema = z.object({
  DATABASE_URL: z.string().url(),
  JWT_SECRET: z.string().min(32),
  REDIS_URL: z.string().url().optional(),
  NODE_ENV: z.enum(['development', 'production', 'test']),
});

const env = EnvSchema.parse(process.env);

// Never hardcode secrets
// ❌ const JWT_SECRET = 'my-secret-key-123';
// ✅ const JWT_SECRET = env.JWT_SECRET;
```

## Best Practices

1. **Never store secrets in code** — use env vars, vault, secrets manager
2. **Always validate inputs** — at system boundaries, use Pydantic
3. **Use ORM parameterized queries** — never concatenate SQL
4. **Enable autoescape** in Jinja2 or any template engine
5. **Implement CSRF protection** for all state-changing operations
6. **Rate limiting** on all public endpoints (login, registration, password reset)
7. **HTTPS everywhere** — redirect HTTP → HTTPS, HSTS header
8. **Password hashing** — argon2 (preferred) or bcrypt, never MD5/SHA1. Use passlib with `deprecated="auto"` for schema migration
9. **JWT with short expiration** + refresh token rotation
10. **Log suspicious events** but NEVER log secrets, passwords, or tokens
11. **Validate file uploads** — check size, MIME type (magic bytes, not header), extension; sanitize filename; store outside webroot
12. **SSRF protection** — for server-side HTTP requests, block private/reserved IP ranges (10/8, 172.16/12, 192.168/16, 127/8, 169.254/16), disable auto-redirect
13. **Replace deprecated libraries** — `bleach` → `nh3` (archived since 2023), use actively maintained alternatives

## Common Pitfalls

| Mistake | Why It's Dangerous | Fix |
|---|---|---|
| Hardcoded credentials | Permanently in git history | Env vars, vault, .gitignore .env |
| `eval(user_input)` | Remote code execution | Use safe alternatives |
| `sql.format(user_input)` | SQL injection | Parameterized queries, ORM |
| No CSRF protection | Account takeover | CSRF tokens for every state-changing request |
| Logging passwords/tokens | Credential leak | Filter sensitive fields from logs |
| Long-lived JWT tokens | Token theft = permanent access | Short expiry + refresh tokens |
| Missing CORS config | Cross-origin attacks | Restrict origins, methods, headers |
| `autoescape=False` in Jinja2 | XSS | Always `autoescape=True` for HTML |
| Passwords without hashing | Data breach = all passwords exposed | argon2/bcrypt with salt via passlib |
| Trusting user-uploaded files | Malware, path traversal | Magic bytes validation, sanitize filename, store outside webroot |
| Server-side fetch without SSRF protection | Access to internal services, cloud metadata (169.254.169.254) | Block private IPs, disable auto-redirect, validate scheme |
| Using deprecated libraries (e.g. `bleach`) | No security patches, known vulnerabilities | Replace with maintained alternatives (`nh3` instead of `bleach`) |

## Context7 Integration

When working with security patterns, verify against current documentation:

| Library | Context7 ID | When to Query |
|---------|-------------|---------------|
| OWASP | (query "OWASP Top 10") | Latest vulnerability categories |
| passlib | (query "passlib") | Password hashing algorithms |
| python-jose | (query "python-jose") | JWT implementation |
| cryptography | (query "cryptography Python") | Encryption, Fernet, certificates |
| nh3 | (query "nh3") | HTML sanitization |

Use `mcp__context7__resolve-library-id` then `mcp__context7__query-docs` to get current examples.