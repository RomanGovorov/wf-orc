# Advanced Patterns: Secure Coding Patterns

> This file extends [`SKILL.md`](SKILL.md) with advanced patterns and edge cases.

## Security Headers (FastAPI Middleware)

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
        # omitting it entirely — CSP is the real control.
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

## Password Hashing — Advanced Techniques

### Timing Attack Prevention

```python
# Constant-time guard for login: a fixed hash used ONLY to ensure
# `verify_password` always runs when the user does not exist, so the
# response time does not leak whether the email is registered.
DUMMY_HASH = hash_password("dummy")

@app.post("/login")
async def login(credentials: LoginSchema):
    user = await get_user_by_email(credentials.email)
    if user is None:
        # Run verify against a dummy hash so timing is indistinguishable
        verify_password(credentials.password, DUMMY_HASH)
        raise HTTPException(401, "Invalid credentials")
    # pwdlib's verify_and_update verifies AND checks if rehash is needed
    valid, new_hash = password_hash.verify_and_update(credentials.password, user.password_hash)
    if not valid:
        raise HTTPException(401, "Invalid credentials")
    if new_hash is not None:
        user.password_hash = new_hash
        await save_user(user)
    token = create_access_token({"sub": str(user.id)})
    return {"access_token": token, "token_type": "bearer"}
```

### Registration with Policy

```python
# Registration — min length 12, NO composition rules (NIST SP 800-63B);
# breached-password check belongs in the Pydantic model (see Pattern 5)
@app.post("/register")
async def register(data: RegisterSchema):
    # Password validation handled by Pydantic schema
    hashed = hash_password(data.password)
    user = await create_user(data.email, hashed)
    return {"id": user.id}
```

## File Upload Security

```python
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
    """Validate file upload: size, MIME type, extension → (content, stored_name)."""
    # 0. Guard: file.filename may be None
    if not file.filename:
        raise HTTPException(415, "Missing filename")

    # 1. Check size BEFORE buffering, then read in bounded chunks
    if file.size is not None and file.size > MAX_FILE_SIZE:
        raise HTTPException(413, f"File too large (max {MAX_FILE_SIZE // 1024 // 1024}MB)")

    chunks: list[bytes] = []
    total = 0
    while True:
        chunk = await file.read(64 * 1024)
        if not chunk:
            break
        total += len(chunk)
        if total > MAX_FILE_SIZE:
            raise HTTPException(413, f"File too large")
        chunks.append(chunk)
    content = b"".join(chunks)

    # 2. Check extension
    ext = Path(file.filename).suffix.lower()
    if ext not in {e for exts in ALLOWED_MIME_TYPES.values() for e in exts}:
        raise HTTPException(415, "File type not allowed")

    # 3. Verify MIME type from content (magic bytes)
    detected_mime = magic.from_buffer(content, mime=True)
    if detected_mime not in ALLOWED_MIME_TYPES:
        raise HTTPException(415, f"Invalid file content (detected: {detected_mime})")

    # 4. Extension matches detected MIME
    if ext not in ALLOWED_MIME_TYPES.get(detected_mime, []):
        raise HTTPException(415, "File extension does not match content")

    # 5. Sanitize filename (prevent path traversal)
    safe_name = Path(file.filename).name  # strips directory components
    safe_name = "".join(c for c in safe_name if c.isalnum() or c in ".-_")
    if safe_name in {"", ".", ".."}:
        raise HTTPException(415, "Invalid filename")

    # 6. Store under uuid-based name
    stored_name = uuid4().hex + ext
    return content, stored_name
```

## SSRF Prevention

```python
import ipaddress
import socket
from urllib.parse import urljoin, urlparse, urlunparse
import httpx

# Denylist of private/reserved ranges — IPv4 AND IPv6
BLOCKED_NETWORKS = [
    ipaddress.ip_network("0.0.0.0/8"),
    ipaddress.ip_network("10.0.0.0/8"),
    ipaddress.ip_network("100.64.0.0/10"),    # CGNAT
    ipaddress.ip_network("127.0.0.0/8"),
    ipaddress.ip_network("169.254.0.0/16"),   # link-local / cloud metadata
    ipaddress.ip_network("172.16.0.0/12"),
    ipaddress.ip_network("192.168.0.0/16"),
    ipaddress.ip_network("::1/128"),
    ipaddress.ip_network("fc00::/7"),         # ULA
    ipaddress.ip_network("fe80::/10"),
    ipaddress.ip_network("::ffff:0:0/96"),    # IPv4-mapped
]

MAX_REDIRECTS = 5

def _is_blocked(ip) -> bool:
    return (
        any(ip in net for net in BLOCKED_NETWORKS)
        or ip.is_private or ip.is_loopback or ip.is_link_local
        or ip.is_reserved or ip.is_multicast or ip.is_unspecified
    )

def resolve_and_validate(hostname: str) -> str:
    """Resolve ALL A/AAAA records; reject if ANY is internal."""
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
    """Fetch URL with SSRF protection. Defeats DNS rebinding via IP pinning."""
    async with httpx.AsyncClient(follow_redirects=False, timeout=timeout) as client:
        for _ in range(MAX_REDIRECTS):
            parsed = urlparse(url)
            if parsed.scheme not in ("http", "https"):
                raise ValueError(f"Blocked scheme: {parsed.scheme}")
            if not parsed.hostname:
                raise ValueError("Missing hostname")

            # IMPORTANT: wrap sync getaddrinfo in asyncio.to_thread
            ip = await asyncio.to_thread(resolve_and_validate, parsed.hostname)

            # Pin: connect to validated IP, keep hostname for TLS (SNI)
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
            if response.is_redirect:
                url = urljoin(url, response.headers["location"])
                continue
            return response
        raise ValueError(f"Too many redirects (>{MAX_REDIRECTS})")
```

## Rate Limiting

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

@app.post("/api/login")
@limiter.limit("5/minute")  # bruteforce protection
async def login(request: Request, credentials: LoginCredentials):
    ...

@app.get("/api/users")
@limiter.limit("100/minute")  # general API limit
async def list_users(request: Request):
    ...
```

## JavaScript/TypeScript Patterns

### SQL Injection Prevention (node-postgres)

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

### XSS Prevention (DOMPurify + React)

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

### CSRF Protection (Express + csrf-csrf)

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

app.post('/api/transfer', doubleCsrfProtection, (req, res) => {
  res.json({ status: 'ok' });
});
```

### Secrets Management (Node.js)

```typescript
import { z } from 'zod';

const EnvSchema = z.object({
  DATABASE_URL: z.url(),
  JWT_SECRET: z.string().min(32),
  REDIS_URL: z.url().optional(),
  NODE_ENV: z.enum(['development', 'production', 'test']),
});

const env = EnvSchema.parse(process.env);
// ❌ const JWT_SECRET = 'my-secret-key-123';
// ✅ const JWT_SECRET = env.JWT_SECRET;
```

## Edge Cases and Deep Dives

### CSRF: Double-Submit Cookie Details

- Server sets CSRF token cookie (`httponly=False`, `Secure`, `SameSite=Lax`)
- Client copies cookie value into `X-CSRF-Token` header
- Server compares cookie vs header in **constant time** (`hmac.compare_digest`)
- `httponly=False` is the standard tradeoff: the cookie is a shared secret, never a session credential
- HTML forms: hidden `csrf_token` field as fallback

### JWT: Common Pitfalls

- **NOT python-jose** — recent CVEs (CVE-2024-33663/33664 algorithm confusion); use PyJWT
- Always require `exp`, `sub`, `iat` claims
- Use `algorithms=[ALGORITHM]` (list) to prevent algorithm confusion
- Short expiration (15-30 min) + refresh token rotation

### File Upload: Why Check Magic Bytes?

The `Content-Type` header is client-controlled and easily spoofed. Always verify the actual file content using `python-magic` (libmagic bindings) which reads the file's magic bytes to determine the true MIME type.

### SSRF: Why Pin the IP?

Without IP pinning, an attacker can exploit DNS rebinding: the first DNS lookup returns a public IP (passes validation), but by the time the HTTP client connects, DNS returns a private IP (TOCTOU attack). Pinning the IP in the connection URL prevents re-resolution.

---

## Additional Resources

- **Core patterns:** See [`SKILL.md`](SKILL.md) for essential patterns
- **Code examples:** See [`examples.md`](examples.md) for complete working examples
