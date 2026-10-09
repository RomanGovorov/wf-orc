# Code Examples: Secure Coding Patterns

> Working examples for [`SKILL.md`](SKILL.md).

## Example 1: Complete CSRF Protection (FastAPI)

```python
# Full CSRF middleware with double-submit cookie pattern
from fastapi import FastAPI, Request, Depends, HTTPException
from fastapi.responses import JSONResponse
from starlette.middleware.sessions import SessionMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
import hmac
import secrets

app = FastAPI()
app.add_middleware(SessionMiddleware, secret_key=settings.secret_key)

class CSRFMiddleware(BaseHTTPMiddleware):
    """CSRF protection via double-submit cookie pattern."""

    UNSAFE_METHODS = {"POST", "PUT", "PATCH", "DELETE"}

    @staticmethod
    def _ensure_token(request: Request, response) -> None:
        """Set the CSRF cookie + header when the client has no cookie yet.

        Called on BOTH the 403 path and the success path so non-browser clients
        can bootstrap a token on their very first POST.
        """
        if "csrf_token" not in request.cookies:
            token = secrets.token_urlsafe(32)
            response.set_cookie(
                "csrf_token", token,
                httponly=False,  # JS must read it to build the X-CSRF-Token header
                secure=True, samesite="lax",
            )
            response.headers["x-csrf-token"] = token

    async def dispatch(self, request: Request, call_next):
        if request.method in self.UNSAFE_METHODS:
            cookie_token = request.cookies.get("csrf_token")
            submitted = request.headers.get("x-csrf-token")
            if not submitted and "form" in request.headers.get("content-type", ""):
                # HTML-form fallback: token may arrive as a body field.
                await request.body()  # cache the body
                form = await request.form()
                submitted = form.get("csrf_token")
            if (
                not cookie_token
                or not submitted
                or not hmac.compare_digest(
                    cookie_token.encode(),
                    str(submitted).encode("latin-1", "ignore")
                )
            ):
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
```

## Example 2: Complete JWT Authentication Flow

```python
import jwt
from datetime import datetime, timedelta, timezone
from fastapi import Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

SECRET_KEY = settings.secret_key  # from pydantic-settings
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

def create_access_token(data: dict) -> str:
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire, "iat": datetime.now(timezone.utc)})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

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

## Example 3: Complete Input Validation with Pydantic

```python
from pydantic import BaseModel, EmailStr, Field, field_validator, constr

class UserCreate(BaseModel):
    email: EmailStr
    password: str = Field(min_length=12, max_length=128)
    username: constr(pattern=r"^[a-zA-Z0-9_]{3,30}$")
    age: int = Field(ge=13, le=120)

    @field_validator("password")
    @classmethod
    def password_not_breached(cls, v: str) -> str:
        # k-anonymity range API (Have I Been Pwned):
        #   1. digest = hashlib.sha1(v.encode()).hexdigest().upper()
        #   2. GET https://api.pwnedpasswords.com/range/{digest[:5]}
        #   3. reject if digest[5:] appears in the returned list
        if is_breached_password(v):
            raise ValueError("Password appears in known breach data — choose another")
        return v

    @field_validator("username")
    @classmethod
    def username_not_reserved(cls, v: str) -> str:
        RESERVED = {"admin", "root", "system", "api"}
        if v.lower() in RESERVED:
            raise ValueError("Username is reserved")
        return v

@app.post("/api/users")
async def create_user(user: UserCreate):
    # Pydantic validates shape/type; SQLi safety from parameterized queries
    ...
```

## Example 4: Complete Secrets Management

```python
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field
import logging

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")
    database_url: str = Field(..., description="PostgreSQL connection string")
    secret_key: str = Field(..., min_length=32)
    jwt_algorithm: str = "HS256"

settings = Settings()  # Raises error if required env vars missing

logger = logging.getLogger(__name__)

SENSITIVE_REQUEST_HEADERS = {"authorization", "proxy-authorization", "cookie", "x-api-key"}
SENSITIVE_RESPONSE_HEADERS = {"set-cookie"}

def redact_headers(headers, sensitive: set[str]) -> dict:
    return {
        k: ("[REDACTED]" if k.lower() in sensitive else v)
        for k, v in dict(headers).items()
    }

# Use in request/response logging
logger.info(
    "request",
    extra={
        "method": request.method,
        "path": request.url.path,
        "headers": redact_headers(request.headers, SENSITIVE_REQUEST_HEADERS),
    },
)
```

## Example 5: Complete Password Hashing with pwdlib

```python
# pip install "pwdlib[argon2,bcrypt]"
from pwdlib import PasswordHash
from pwdlib.hashers.argon2 import Argon2Hasher
from pwdlib.hashers.bcrypt import BcryptHasher

# Argon2id first; bcrypt ONLY for verifying legacy hashes
password_hash = PasswordHash((Argon2Hasher(), BcryptHasher()))

def hash_password(password: str) -> str:
    return password_hash.hash(password)

def verify_password(plain: str, hashed: str) -> bool:
    return password_hash.verify(plain, hashed)

# Timing-safe login
DUMMY_HASH = hash_password("dummy")

@app.post("/login")
async def login(credentials: LoginSchema):
    user = await get_user_by_email(credentials.email)
    if user is None:
        verify_password(credentials.password, DUMMY_HASH)
        raise HTTPException(401, "Invalid credentials")

    valid, new_hash = password_hash.verify_and_update(
        credentials.password, user.password_hash
    )
    if not valid:
        raise HTTPException(401, "Invalid credentials")
    if new_hash is not None:
        user.password_hash = new_hash
        await save_user(user)

    token = create_access_token({"sub": str(user.id)})
    return {"access_token": token, "token_type": "bearer"}
```

## Example 6: Complete File Upload Validation

```python
import magic
from pathlib import Path
from uuid import uuid4
from fastapi import UploadFile, HTTPException

ALLOWED_MIME_TYPES = {
    "image/jpeg": [".jpg", ".jpeg"],
    "image/png": [".png"],
    "application/pdf": [".pdf"],
}
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10 MB

async def validate_upload(file: UploadFile) -> tuple[bytes, str]:
    if not file.filename:
        raise HTTPException(415, "Missing filename")

    # Size check via bounded reads
    if file.size is not None and file.size > MAX_FILE_SIZE:
        raise HTTPException(413, f"File too large")

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

    # Extension check
    ext = Path(file.filename).suffix.lower()
    allowed_exts = {e for exts in ALLOWED_MIME_TYPES.values() for e in exts}
    if ext not in allowed_exts:
        raise HTTPException(415, "File type not allowed")

    # Magic bytes verification
    detected_mime = magic.from_buffer(content, mime=True)
    if detected_mime not in ALLOWED_MIME_TYPES:
        raise HTTPException(415, f"Invalid file content")
    if ext not in ALLOWED_MIME_TYPES.get(detected_mime, []):
        raise HTTPException(415, "Extension does not match content")

    # Sanitize filename
    safe_name = Path(file.filename).name
    safe_name = "".join(c for c in safe_name if c.isalnum() or c in ".-_")
    if safe_name in {"", ".", ".."}:
        raise HTTPException(415, "Invalid filename")

    # UUID-based storage name
    stored_name = uuid4().hex + ext
    return content, stored_name
```

## Example 7: JavaScript/TypeScript Security Patterns

### Zod Schema Validation

```typescript
import { z } from 'zod';

const UserSchema = z.object({
  email: z.string().email(),
  password: z.string().min(12).max(128),
  username: z.string().regex(/^[a-zA-Z0-9_]{3,30}$/),
  age: z.number().int().min(13).max(120),
});

// In Express handler
app.post('/api/users', (req, res) => {
  const result = UserSchema.safeParse(req.body);
  if (!result.success) {
    return res.status(400).json({ errors: result.error.flatten() });
  }
  // result.data is fully typed and validated
  const user = createUser(result.data);
  res.status(201).json(user);
});
```

### DOMPurify for XSS Prevention

```typescript
import DOMPurify from 'dompurify';

const ALLOWED_TAGS = ['b', 'i', 'em', 'strong', 'a', 'p', 'ul', 'ol', 'li'];
const ALLOWED_ATTR = ['href', 'rel'];

function sanitizeHtml(input: string): string {
  return DOMPurify.sanitize(input, {
    ALLOWED_TAGS,
    ALLOWED_ATTR,
    USE_PROFILES: { html5: true },
  });
}

// Usage in React
function UserContent({ html }: { html: string }) {
  const clean = sanitizeHtml(html);
  return <div dangerouslySetInnerHTML={{ __html: clean }} />;
}
```

---

## Additional Resources

- **Core patterns:** See [`SKILL.md`](SKILL.md) for essential patterns
- **Advanced techniques:** See [`advanced.md`](advanced.md) for deep dives and edge cases
