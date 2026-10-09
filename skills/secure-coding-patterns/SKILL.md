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

### Pattern 1: SQL Injection Prevention

```python
# ❌ BAD: String formatting / concatenation
query = f"SELECT * FROM users WHERE email = '{user_email}'"
cursor.execute(query)

# ✅ GOOD: Parameterized queries
cursor.execute("SELECT * FROM users WHERE email = %s", (user_email,))

# ✅ GOOD: ORM with proper expressions (SQLAlchemy 2.0)
from sqlalchemy import select
stmt = select(User).where(User.email == user_email)
user = db.session.scalar(stmt)
```

### Pattern 2: XSS Prevention

```python
# ✅ GOOD: Jinja2 with autoescape
from jinja2 import Environment, FileSystemLoader, select_autoescape
env = Environment(
    loader=FileSystemLoader("templates"),
    autoescape=select_autoescape(["html", "xml"]),
)

# ✅ GOOD: Sanitize HTML with nh3 (bleach is deprecated/archived since 2023)
# pip install nh3
import nh3
ALLOWED_TAGS = {"p", "b", "i", "em", "strong", "a", "ul", "ol", "li"}
ALLOWED_ATTRIBUTES = {"a": {"href", "rel"}}
clean_html = nh3.clean(user_html, tags=ALLOWED_TAGS, attributes=ALLOWED_ATTRIBUTES)
```

### Pattern 3: CSRF Protection

```python
# Double-submit cookie pattern (recommended for SPAs)
# - Server sets CSRF token cookie (httponly=False, Secure, SameSite=Lax)
# - Client echoes token in X-CSRF-Token header
# - Server compares cookie vs header in CONSTANT time

from starlette.middleware.base import BaseHTTPMiddleware
import hmac, secrets

class CSRFMiddleware(BaseHTTPMiddleware):
    UNSAFE_METHODS = {"POST", "PUT", "PATCH", "DELETE"}

    async def dispatch(self, request: Request, call_next):
        if request.method in self.UNSAFE_METHODS:
            cookie_token = request.cookies.get("csrf_token")
            submitted = request.headers.get("x-csrf-token")
            if (
                not cookie_token
                or not submitted
                or not hmac.compare_digest(
                    cookie_token.encode(),
                    str(submitted).encode("latin-1", "ignore")
                )
            ):
                return JSONResponse(status_code=403, content={"detail": "CSRF validation failed"})
        return await call_next(request)
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
    expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire, "iat": datetime.now(timezone.utc)})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

def verify_token(token: str) -> dict:
    try:
        return jwt.decode(
            token, SECRET_KEY, algorithms=[ALGORITHM],
            options={"require": ["exp", "sub", "iat"]},
        )
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")
```

### Pattern 5: Input Validation with Pydantic

```python
from pydantic import BaseModel, EmailStr, Field, field_validator, constr

class UserCreate(BaseModel):
    email: EmailStr
    # NIST SP 800-63B / OWASP: enforce LENGTH (min 12), NOT composition rules
    password: str = Field(min_length=12, max_length=128)
    username: constr(pattern=r"^[a-zA-Z0-9_]{3,30}$")
    age: int = Field(ge=13, le=120)

    @field_validator("password")
    @classmethod
    def password_not_breached(cls, v: str) -> str:
        if is_breached_password(v):  # implement via k-anonymity range API
            raise ValueError("Password appears in known breach data — choose another")
        return v
```

### Pattern 6: Secrets Management

```python
# ❌ BAD: Hardcoded secrets or defaults for sensitive values
DB_PASSWORD = "super_secret_123"
config = {"database": {"password": os.environ.get("DB_PASS", "default_password")}}

# ✅ GOOD: pydantic-settings — mandatory, no defaults for secrets
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")
    database_url: str = Field(..., description="PostgreSQL connection string")
    secret_key: str = Field(..., min_length=32)

settings = Settings()  # Raises error if required env vars missing

# ✅ GOOD: Redact sensitive headers before LOGGING
SENSITIVE_HEADERS = {"authorization", "proxy-authorization", "cookie", "x-api-key", "set-cookie"}
def redact_headers(headers, sensitive: set[str]) -> dict:
    return {k: ("[REDACTED]" if k.lower() in sensitive else v) for k, v in dict(headers).items()}
```

### Pattern 7: Password Hashing (pwdlib / argon2-cffi)

```python
# passlib is UNMAINTAINED (last release 2020; broken on Python 3.13+).
# Use pwdlib or argon2-cffi directly.
# pip install "pwdlib[argon2,bcrypt]"
from pwdlib import PasswordHash
from pwdlib.hashers.argon2 import Argon2Hasher
from pwdlib.hashers.bcrypt import BcryptHasher

# Argon2id for NEW hashes; bcrypt kept ONLY to verify legacy hashes
password_hash = PasswordHash((Argon2Hasher(), BcryptHasher()))

def hash_password(password: str) -> str:
    return password_hash.hash(password)

def verify_password(plain: str, hashed: str) -> bool:
    return password_hash.verify(plain, hashed)

# Login: use verify_and_update for transparent rehashing
valid, new_hash = password_hash.verify_and_update(password, user.password_hash)
if not valid:
    raise HTTPException(401, "Invalid credentials")
if new_hash is not None:
    user.password_hash = new_hash  # persist upgraded hash
```

## Key Pitfalls

| Mistake | Why It's Dangerous | Fix |
|---|---|---|
| Hardcoded credentials | Permanently in git history | Env vars, vault, .gitignore .env |
| `eval(user_input)` | Remote code execution | Use safe alternatives |
| `sql.format(user_input)` | SQL injection | Parameterized queries, ORM |
| No CSRF protection | Account takeover | CSRF tokens for state-changing requests |
| Logging passwords/tokens | Credential leak | Filter sensitive fields from logs |
| Long-lived JWT tokens | Token theft = permanent access | Short expiry + refresh tokens |
| `autoescape=False` in Jinja2 | XSS | Always `autoescape=True` for HTML |
| Passwords without hashing | Data breach = all passwords exposed | Argon2id/bcrypt via pwdlib or argon2-cffi |
| Trusting user-uploaded files | Malware, path traversal | Magic bytes, sanitize filename, store outside webroot |
| Server-side fetch without SSRF protection | Access to internal services, cloud metadata | Block private IPs (v4+v6), pin to validated IP |
| Using deprecated libraries (`bleach`) | No security patches | Replace with maintained alternatives (`nh3`) |

## Best Practices

1. **Never store secrets in code** — use env vars, vault, secrets manager
2. **Always validate inputs** — at system boundaries, use Pydantic
3. **Use ORM parameterized queries** — never concatenate SQL
4. **Enable autoescape** in Jinja2 or any template engine
5. **Implement CSRF protection** for all state-changing operations
6. **Rate limiting** on all public endpoints (login, registration, password reset)
7. **HTTPS everywhere** — redirect HTTP → HTTPS, HSTS header
8. **Password hashing & policy** — Argon2id (preferred) or bcrypt, never MD5/SHA1. Use pwdlib or argon2-cffi (passlib is unmaintained). Policy: min length 12, no composition rules (NIST SP 800-63B), breached-password check via k-anonymity API
9. **JWT with short expiration** + refresh token rotation
10. **Log suspicious events** but NEVER log secrets, passwords, or tokens
11. **Validate file uploads** — check size, MIME type (magic bytes), extension; sanitize filename; store outside webroot
12. **SSRF protection** — block private/reserved ranges (IPv4 AND IPv6), resolve ALL DNS records and PIN connection, manual redirect validation with depth limit
13. **Replace deprecated libraries** — `bleach` → `nh3` (archived since 2023)

## Additional Resources

- **Advanced patterns:** See [`advanced.md`](advanced.md) for security headers, file upload security, SSRF prevention, rate limiting, and JavaScript/TypeScript patterns
- **Code examples:** See [`examples.md`](examples.md) for complete working examples and templates

## See also

> **See also**: `api-design-principles` — API validation patterns, pagination, error handling.
> **See also**: `javascript-typescript-professional` — Zod schema validation, type inference, transforms.

## Context7 Integration

When Context7 MCP tools are available in your session, use them to fetch up-to-date library documentation instead of relying on memory. Tool names vary by installation (e.g. `mcp__context7__resolve-library-id` / `mcp__context7__query-docs`, or plugin-prefixed variants such as `mcp__plugin_context7_context7__*`) — check the available-tools listing for the exact names. Always resolve the library ID first; the IDs in the table below are examples and may change.

| Library | Context7 ID | When to Query |
|---------|-------------|---------------|
| OWASP | (query "OWASP Top 10") | Latest vulnerability categories |
| pwdlib | (query "pwdlib") | Password hashing (maintained passlib replacement) |
| PyJWT | `/jpadilla/pyjwt` (query "PyJWT") | JWT encode/decode, exceptions — NOT python-jose (recent CVEs) |
| cryptography | (query "cryptography Python") | Encryption, Fernet, certificates |
| nh3 | (query "nh3") | HTML sanitization |
