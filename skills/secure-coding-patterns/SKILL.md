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
from fastapi.responses import JSONResponse
from starlette.middleware.sessions import SessionMiddleware
import hmac
import secrets

app = FastAPI()
# settings comes from pydantic-settings: class Settings(BaseSettings): secret_key: str = Field(..., min_length=32)
app.add_middleware(SessionMiddleware, secret_key=settings.secret_key)

# Option 1: Double-submit cookie pattern (recommended for SPAs)
# - Server sets a CSRF token cookie that browser JS CAN read (httponly=False,
#   Secure, SameSite=Lax) — otherwise the SPA cannot echo it back
# - Client copies the cookie value into the X-CSRF-Token header
#   (HTML forms: hidden csrf_token field — read as a fallback below)
# - Server compares cookie vs header/field in CONSTANT time
#   (httponly=False is the standard double-submit tradeoff: the cookie is a
#   shared secret, never a session credential)

# Option 2: Custom middleware approach
from starlette.middleware.base import BaseHTTPMiddleware

class CSRFMiddleware(BaseHTTPMiddleware):
    """CSRF protection via double-submit cookie pattern."""

    UNSAFE_METHODS = {"POST", "PUT", "PATCH", "DELETE"}

    @staticmethod
    def _ensure_token(request: Request, response) -> None:
        """Set the CSRF cookie + header when the client has no cookie yet.

        Called on BOTH the 403 path and the success path so non-browser clients
        can bootstrap a token on their very first POST (otherwise the 403
        early-return would skip cookie-setting and the client could never
        obtain a token to retry with).
        """
        if "csrf_token" not in request.cookies:
            token = secrets.token_urlsafe(32)
            response.set_cookie(
                "csrf_token", token,
                httponly=False,  # JS must read it to build the X-CSRF-Token header
                secure=True, samesite="lax",
            )
            # Also expose the token in a response header so clients can pick
            # it up without cookie access (first response, non-browser clients)
            response.headers["x-csrf-token"] = token

    async def dispatch(self, request: Request, call_next):
        if request.method in self.UNSAFE_METHODS:
            cookie_token = request.cookies.get("csrf_token")
            submitted = request.headers.get("x-csrf-token")
            if not submitted and "form" in request.headers.get("content-type", ""):
                # HTML-form fallback: token may arrive as a body field.
                # IMPORTANT: call `body()` first — Starlette's _CachedRequest only
                # replays the body downstream if `body()` was invoked. For multipart
                # requests, `form()` consumes the stream without caching, which would
                # leave the downstream handler with an empty body.
                await request.body()  # cache the body
                form = await request.form()
                submitted = form.get("csrf_token")
            # Constant-time comparison — never `!=` on secrets
            if (
                not cookie_token
                or not submitted
                or not hmac.compare_digest(cookie_token.encode(), str(submitted).encode("latin-1", "ignore"))
            ):
                # Return a JSONResponse: an HTTPException raised inside a
                # BaseHTTPMiddleware bypasses FastAPI's exception handlers
                # (it would surface as a 500, not a 403).
                response = JSONResponse(
                    status_code=403,
                    content={"detail": "CSRF validation failed"},
                )
                self._ensure_token(request, response)
                return response
        response = await call_next(request)
        self._ensure_token(request, response)
        return response

app.add_middleware(CSRFMiddleware)

@app.post("/api/users")
async def create_user(request: Request, data: UserCreate):
    # CSRF validated by middleware before reaching this handler
    ...

# HTML forms — submit the token as a hidden field (the middleware reads
# `csrf_token` from the form body as a fallback):
# <form method="POST">
#     <input type="hidden" name="csrf_token" value="{{ csrf_token }}">
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

# Callers MUST put the user id in "sub" — get_current_user reads it below:
# token = create_access_token({"sub": str(user.id)})

def verify_token(token: str) -> dict:
    try:
        payload = jwt.decode(
            token, SECRET_KEY, algorithms=[ALGORITHM],
            options={"require": ["exp", "sub", "iat"]},
        )
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

class UserCreate(BaseModel):
    # ✅ Type-safe constraints
    email: EmailStr
    # NIST SP 800-63B / OWASP: enforce LENGTH (min 12), NOT composition
    # rules (uppercase/digit requirements) — composition adds little entropy
    # and pushes users toward predictable patterns ("Passw0rd!").
    password: str = Field(min_length=12, max_length=128)
    username: constr(pattern=r"^[a-zA-Z0-9_]{3,30}$")
    age: int = Field(ge=13, le=120)

    @field_validator("password")
    @classmethod
    def password_not_breached(cls, v: str) -> str:
        # Instead of composition rules, reject known-breached passwords using
        # a k-anonymity range API (e.g. Have I Been Pwned):
        #   1. digest = hashlib.sha1(v.encode()).hexdigest().upper()
        #   2. GET https://api.pwnedpasswords.com/range/{digest[:5]}
        #      (only the first 5 hash chars ever leave the client)
        #   3. reject if digest[5:] appears in the returned SUFFIX:count list
        if is_breached_password(v):  # implement via k-anonymity range API
            raise ValueError("Password appears in known breach data — choose another")
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
    # Pydantic validates shape/type only — SQLi safety comes from
    # parameterized queries, XSS safety from output encoding (Patterns 1–2)
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

# ✅ GOOD: redact sensitive headers before LOGGING.
# Note: stripping Authorization/Cookie from live RESPONSES is a no-op control —
# those are REQUEST headers and essentially never appear on responses. The
# genuinely sensitive RESPONSE header is Set-Cookie. Redact both sides in logs.
import logging

logger = logging.getLogger(__name__)

SENSITIVE_REQUEST_HEADERS = {"authorization", "proxy-authorization", "cookie", "x-api-key"}
SENSITIVE_RESPONSE_HEADERS = {"set-cookie"}

def redact_headers(headers, sensitive: set[str]) -> dict:
    """Copy of headers that is safe to log — secrets masked, keys preserved."""
    return {
        k: ("[REDACTED]" if k.lower() in sensitive else v)
        for k, v in dict(headers).items()
    }

# Use in request/response logging — never log the raw headers:
logger.info(
    "request",
    extra={
        "method": request.method,
        "path": request.url.path,
        "headers": redact_headers(request.headers, SENSITIVE_REQUEST_HEADERS),
    },
)
logger.info(
    "response",
    extra={
        "status_code": response.status_code,
        "headers": redact_headers(response.headers, SENSITIVE_RESPONSE_HEADERS),
    },
)
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
        # Do NOT set X-XSS-Protection: the browser XSS auditors it controlled
        # were removed from all modern browsers, and "1; mode=block"
        # historically ENABLED cross-site information leaks. OWASP/MDN advise
        # omitting it entirely ("0" at most, for legacy clients) — CSP is the
        # real control.
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
# passlib is UNMAINTAINED (last release 1.7.4 in 2020; spurious errors with
# bcrypt>=4.x; broken on Python 3.13+ where the `crypt` module was removed).
# Use pwdlib (from the FastAPI Users author) or argon2-cffi directly.
# pip install "pwdlib[argon2,bcrypt]"
from pwdlib import PasswordHash
from pwdlib.hashers.argon2 import Argon2Hasher
from pwdlib.hashers.bcrypt import BcryptHasher

# Argon2id first — used for all NEW hashes. Bcrypt is kept ONLY to verify
# legacy hashes so they can be transparently re-hashed on login (pwdlib's
# equivalent of passlib's deprecated="auto").
password_hash = PasswordHash((Argon2Hasher(), BcryptHasher()))
# No legacy hashes to support? PasswordHash.recommended() → Argon2, sane defaults.

def hash_password(password: str) -> str:
    """Hash password with Argon2id (preferred). Never MD5/SHA1 — far too fast."""
    return password_hash.hash(password)

def verify_password(plain: str, hashed: str) -> bool:
    """Verify password against argon2 or legacy bcrypt hash."""
    return password_hash.verify(plain, hashed)

# Constant-time guard for login: a fixed hash used ONLY to ensure
# `verify_password` always runs when the user does not exist, so the
# response time does not leak whether the email is registered.
DUMMY_HASH = hash_password("dummy")

# Registration — min length 12, NO composition rules (NIST SP 800-63B);
# breached-password check belongs in the Pydantic model (see Pattern 5)
@app.post("/register")
async def register(data: RegisterSchema):
    # Password validation handled by Pydantic schema (RegisterSchema.password has min_length=12).
    hashed = hash_password(data.password)
    user = await create_user(data.email, hashed)
    return {"id": user.id}

# Login
@app.post("/login")
async def login(credentials: LoginSchema):
    user = await get_user_by_email(credentials.email)
    if user is None:
        # Run verify against a dummy hash so the timing is indistinguishable
        # from a real password check — prevents a timing oracle that leaks
        # whether the email is registered.
        verify_password(credentials.password, DUMMY_HASH)
        raise HTTPException(401, "Invalid credentials")
    # pwdlib's `verify_and_update` verifies AND checks if rehash is needed in one call.
    # Returns (valid, new_hash); new_hash is non-None when the stored hash used a
    # deprecated scheme or outdated parameters — persist it to migrate transparently.
    valid, new_hash = password_hash.verify_and_update(credentials.password, user.password_hash)
    if not valid:
        raise HTTPException(401, "Invalid credentials")
    if new_hash is not None:
        user.password_hash = new_hash
        await save_user(user)
    # Pattern 4 signature is create_access_token(data: dict) — "sub" required
    token = create_access_token({"sub": str(user.id)})
    return {"access_token": token, "token_type": "bearer"}
```

### Pattern 10: File Upload Security

```python
# Pattern 10: File Upload Security
import magic  # python-magic
from pathlib import Path
from uuid import uuid4

ALLOWED_MIME_TYPES = {
    "image/jpeg": [".jpg", ".jpeg"],
    "image/png": [".png"],
    "application/pdf": [".pdf"],
}
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10 MB

async def validate_upload(file: UploadFile) -> tuple[bytes, str]:
    """Validate file upload: size, MIME type, extension → (content, stored_name).

    The returned name is a collision-free uuid-based filename safe for storage
    outside the webroot — the original filename is never used as-is.
    """
    # 0. Guard: file.filename may be None (multipart without a filename part)
    if not file.filename:
        raise HTTPException(415, "Missing filename")

    # 1. Check size BEFORE buffering: cheap early reject via file.size
    #    (from the parsed multipart data; may be None)...
    if file.size is not None and file.size > MAX_FILE_SIZE:
        raise HTTPException(413, f"File too large (max {MAX_FILE_SIZE // 1024 // 1024}MB)")

    # ...then the authoritative guard: read in bounded chunks and abort the
    # moment the limit is exceeded. NEVER `await file.read()` an untrusted
    # upload whole — a huge file would be buffered in memory first (DoS).
    chunks: list[bytes] = []
    total = 0
    while True:
        chunk = await file.read(64 * 1024)
        if not chunk:
            break
        total += len(chunk)
        if total > MAX_FILE_SIZE:
            raise HTTPException(413, f"File too large (max {MAX_FILE_SIZE // 1024 // 1024}MB)")
        chunks.append(chunk)
    content = b"".join(chunks)

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

    # 5. Sanitize filename (prevent path traversal / traversal-via-special-names)
    safe_name = Path(file.filename).name  # strips directory components
    safe_name = "".join(c for c in safe_name if c.isalnum() or c in ".-_")
    if safe_name in {"", ".", ".."}:
        raise HTTPException(415, "Invalid filename")

    # 6. Store under a uuid-based name to avoid collisions and prevent any
    #    remnant of the original filename from reaching the filesystem.
    stored_name = uuid4().hex + ext
    return content, stored_name
```

### Pattern 11: SSRF Prevention

```python
# Pattern 11: SSRF Prevention
import ipaddress
import socket
from urllib.parse import urljoin, urlparse, urlunparse
import httpx

# Denylist of private/reserved ranges — IPv4 AND IPv6. A denylist alone is
# not sufficient (some public IPs route internally, e.g. NAT hairpinning);
# pair it with an egress firewall/proxy allowlist for defense in depth.
BLOCKED_NETWORKS = [
    # IPv4
    ipaddress.ip_network("0.0.0.0/8"),        # "this" network
    ipaddress.ip_network("10.0.0.0/8"),       # private
    ipaddress.ip_network("100.64.0.0/10"),    # CGNAT / carrier infra
    ipaddress.ip_network("127.0.0.0/8"),      # loopback
    ipaddress.ip_network("169.254.0.0/16"),   # link-local / cloud metadata
    ipaddress.ip_network("172.16.0.0/12"),    # private
    ipaddress.ip_network("192.168.0.0/16"),   # private
    # IPv6
    ipaddress.ip_network("::1/128"),          # loopback
    ipaddress.ip_network("fc00::/7"),         # unique-local address (ULA)
    ipaddress.ip_network("fe80::/10"),        # link-local
    ipaddress.ip_network("::ffff:0:0/96"),    # IPv4-mapped — smuggles IPv4 in
]

MAX_REDIRECTS = 5

def _is_blocked(ip: ipaddress.IPv4Address | ipaddress.IPv6Address) -> bool:
    """True if private/reserved by denylist or by stdlib classification."""
    return (
        any(ip in net for net in BLOCKED_NETWORKS)
        or ip.is_private or ip.is_loopback or ip.is_link_local
        or ip.is_reserved or ip.is_multicast or ip.is_unspecified
    )

def resolve_and_validate(hostname: str) -> str:
    """Resolve ALL A/AAAA records; reject if ANY is internal.

    Returns one validated IP to pin the connection to. Checking only the
    first record lets an attacker alternate public/internal answers.
    """
    try:
        infos = socket.getaddrinfo(hostname, None, proto=socket.IPPROTO_TCP)
    except socket.gaierror:
        raise ValueError(f"Cannot resolve hostname: {hostname}")
    ips = [ipaddress.ip_address(info[4][0]) for info in infos]
    if not ips:
        raise ValueError(f"No addresses for hostname: {hostname}")
    if any(_is_blocked(ip) for ip in ips):
        raise ValueError(f"Hostname resolves to a blocked IP: {hostname}")
    return str(ips[0])

async def safe_fetch(url: str, timeout: float = 5.0) -> httpx.Response:
    """Fetch a URL with SSRF protection.

    Defeats DNS rebinding (TOCTOU): validate once, then PIN the connection
    to the validated IP so httpx never resolves DNS again. Redirects are
    followed manually, re-validating each hop, with a hard depth limit.
    """
    import asyncio
    async with httpx.AsyncClient(follow_redirects=False, timeout=timeout) as client:
        for _ in range(MAX_REDIRECTS):
            parsed = urlparse(url)

            # 1. Only allow http/https schemes
            if parsed.scheme not in ("http", "https"):
                raise ValueError(f"Blocked scheme: {parsed.scheme}")
            if not parsed.hostname:
                raise ValueError("Missing hostname")

            # 2-3. Resolve ALL records; reject if ANY is private/reserved.
            # IMPORTANT: wrap sync getaddrinfo in asyncio.to_thread — blocking
            # the event loop on DNS is a trivial DoS amplification (one slow
            # resolver stalls ALL concurrent requests for the resolver timeout).
            ip = await asyncio.to_thread(resolve_and_validate, parsed.hostname)

            # 4. Pin: connect to the validated IP, keeping the original
            #    hostname for the Host header and for TLS (SNI + certificate
            #    hostname check) via httpx's official `sni_hostname` request
            #    extension — full TLS verification stays on, no `verify=False`.
            port = parsed.port or (443 if parsed.scheme == "https" else 80)
            default_port = 443 if parsed.scheme == "https" else 80
            host_header = (
                parsed.hostname if port == default_port
                else f"{parsed.hostname}:{port}"
            )
            ip_literal = f"[{ip}]" if ":" in ip else ip
            pinned = urlunparse(parsed._replace(netloc=f"{ip_literal}:{port}"))
            response = await client.get(
                pinned,
                headers={"Host": host_header},
                extensions={"sni_hostname": parsed.hostname},
            )

            # 5. Manual redirect loop — each next hop is re-validated above
            if response.is_redirect:
                url = urljoin(url, response.headers["location"])
                continue
            return response
        raise ValueError(f"Too many redirects (>{MAX_REDIRECTS})")
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
  DATABASE_URL: z.url(),
  JWT_SECRET: z.string().min(32),
  REDIS_URL: z.url().optional(),
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
8. **Password hashing & policy** — Argon2id (preferred) or bcrypt, never MD5/SHA1. Use pwdlib or argon2-cffi (passlib is unmaintained); keep legacy schemes verify-only and rehash on login via pwdlib's `verify_and_update` (returns `(valid, new_hash)` — persist `new_hash` when non-None). Policy: min length 12, no composition rules (NIST SP 800-63B), breached-password check via k-anonymity API
9. **JWT with short expiration** + refresh token rotation
10. **Log suspicious events** but NEVER log secrets, passwords, or tokens
11. **Validate file uploads** — check size, MIME type (magic bytes, not header), extension; sanitize filename; store outside webroot
12. **SSRF protection** — for server-side HTTP requests, block private/reserved ranges for IPv4 AND IPv6 (incl. 100.64/10 CGNAT, 0/8, fc00::/7 ULA, fe80::/10, ::ffff:0:0/96), resolve ALL DNS records and PIN the connection to the validated IP (no re-resolution), disable auto-redirects and re-validate each hop with a depth limit
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
| Passwords without hashing | Data breach = all passwords exposed | Argon2id/bcrypt with salt via pwdlib or argon2-cffi (passlib is unmaintained) |
| Trusting user-uploaded files | Malware, path traversal | Magic bytes validation, sanitize filename, store outside webroot |
| Server-side fetch without SSRF protection | Access to internal services, cloud metadata (169.254.169.254) | Block private IPs (v4+v6), resolve all records + pin to validated IP, manual redirect validation with depth limit, validate scheme |
| Using deprecated libraries (e.g. `bleach`) | No security patches, known vulnerabilities | Replace with maintained alternatives (`nh3` instead of `bleach`) |

## Context7 Integration

When Context7 MCP tools are available in your session, use them to fetch up-to-date library documentation instead of relying on memory. Tool names vary by installation (e.g. `mcp__context7__resolve-library-id` / `mcp__context7__query-docs`, or plugin-prefixed variants such as `mcp__plugin_context7_context7__*`) — check the available-tools listing for the exact names. Always resolve the library ID first; the IDs in the table below are examples and may change.

| Library | Context7 ID | When to Query |
|---------|-------------|---------------|
| OWASP | (query "OWASP Top 10") | Latest vulnerability categories |
| pwdlib | (query "pwdlib") | Password hashing (maintained passlib replacement) |
| PyJWT | `/jpadilla/pyjwt` (query "PyJWT") | JWT encode/decode, exceptions — NOT python-jose (recent CVEs, e.g. CVE-2024-33663/33664 algorithm confusion) |
| cryptography | (query "cryptography Python") | Encryption, Fernet, certificates |
| nh3 | (query "nh3") | HTML sanitization |