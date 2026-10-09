---
name: testing-patterns
description: Testing patterns — test pyramid, fixtures, mocking, property-based testing, integration and E2E tests. Use when creating tests, reviewing code with tests, setting up CI.
priority: 10
paths:
  - "**/test/**"
  - "**/tests/**"
  - "**/test_*.py"
  - "**/*_test.py"
  - "**/*_test.go"
  - "**/*.spec.ts"
  - "**/*.spec.tsx"
  - "**/*.spec.js"
  - "**/*.test.ts"
  - "**/*.test.js"
  - "**/conftest.py"
  - "**/test-utils*"
  - "**/test-helpers*"
  - "**/factories*"
  - "**/jest.config*"
  - "**/pytest.ini"
---

# Testing Patterns

Template for building a reliable test pyramid: from unit to integration and E2E tests. Focus on testability, isolation, and reproducibility.

## When to Use This Skill

- When writing unit tests for new code
- When creating integration tests (DB, HTTP, queues)
- When setting up test fixtures and mocking
- When reviewing tests for coverage quality
- When optimizing test execution time
- When refactoring tests to eliminate flakiness

## Core Concepts

### 1. Test Pyramid

```
        E2E (slow, expensive, low coverage)
       /    \
   Integration (medium, verify interactions)
  /            \
Unit (fast, cheap, high coverage)
```

- **Unit**: one class/function, mocks of external dependencies, <1ms each
- **Integration**: 2+ components, real DB or HTTP service
- **E2E**: full stack, browser/API, minimum critical paths

### 2. AAA Pattern (Arrange-Act-Assert)

```python
def test_user_creation():
    # Arrange — prepare data
    data = {"name": "John", "email": "john@example.com"}

    # Act — perform the action
    user = UserService.create(data)

    # Assert — verify the result
    assert user.name == "John"
    assert user.email == "john@example.com"
    assert user.id is not None
```

### 3. Test Isolation

Each test must be independent:
- Not depend on execution order
- Not share state between tests
- Clean up resources after itself (fixtures, teardown)

## Patterns

### Pattern 1: Pytest Fixtures (Dependency Injection)

```python
# conftest.py — shared fixtures and canonical test doubles
import pytest
from unittest.mock import AsyncMock

class FakeUserRepository:
    """In-memory test double. API mirrors database-patterns repository."""
    def __init__(self):
        self._store: dict[int, dict] = {}
        self._next_id = 1

    def add(self, data: dict) -> dict:
        user = {**data, "id": self._next_id}
        self._store[self._next_id] = user
        self._next_id += 1
        return user

    def get(self, user_id: int) -> dict | None:
        return self._store.get(user_id)

    def list(self, *, offset: int = 0, limit: int = 100) -> list[dict]:
        users = sorted(self._store.values(), key=lambda u: u["id"])
        return users[offset : offset + limit]

    def delete(self, user_id: int) -> bool:
        return self._store.pop(user_id, None) is not None


class UserService:
    """Canonical service — always constructed with (repo, email_service)."""
    def __init__(self, repo, email_service=None):
        self.repo = repo
        self.email_service = email_service

    def create(self, data: dict) -> dict:
        user = self.repo.add(data)
        if self.email_service:
            self.email_service.send(to=data.get("email"), template="welcome")
        return user


@pytest.fixture
def user_repo():
    """Fresh in-memory repository per test."""
    return FakeUserRepository()

@pytest.fixture
def mock_email_service():
    """Mock external email service."""
    mock = AsyncMock()
    mock.send.return_value = {"message_id": "test-123"}
    return mock

@pytest.fixture
def user_service(user_repo, mock_email_service):
    """Service with mocked dependencies."""
    return UserService(repo=user_repo, email_service=mock_email_service)
```

### Pattern 2: Parametrized Tests

```python
import pytest

# Password POLICY (canonical: secure-coding-patterns, NIST SP 800-63B):
# min length 12, NO composition rules, breach-list check recommended.

@pytest.mark.parametrize("password,expected_error", [
    ("short", "at least 12 characters"),
    ("Secure123!", "at least 12 characters"),    # composition doesn't compensate
    ("correct-horse-battery", None),             # 12+ chars — valid
    ("password123456789", "known breach data"),  # long but breached
])
def test_password_validation(password, expected_error):
    if expected_error:
        with pytest.raises(ValueError, match=expected_error):
            validate_password(password)
    else:
        assert validate_password(password) is True

@pytest.mark.parametrize("endpoint,method", [
    ("/api/users", "GET"),
    ("/api/users/1", "GET"),
    ("/api/orders", "GET"),
])
def test_endpoints_require_auth(client, endpoint, method):
    response = getattr(client, method.lower())(endpoint)
    assert response.status_code == 401
```

### Pattern 3: Async Test Patterns

```python
import pytest
from unittest.mock import AsyncMock

@pytest.mark.asyncio
async def test_async_user_creation(user_service, user_data):
    expected_email = user_data["email"]
    user = await user_service.create_async(user_data)
    assert user["email"] == expected_email
    assert user["id"] is not None

@pytest.mark.asyncio
async def test_service_handles_external_failure():
    """Service should handle external service failures gracefully."""
    mock_payment = AsyncMock()
    mock_payment.process.side_effect = ConnectionError("Payment gateway down")
    service = OrderService(payment_service=mock_payment)

    with pytest.raises(ServiceError, match="Payment unavailable"):
        await service.create_order({"items": [{"id": 1, "qty": 2}], "total": 29.99})
```

### Pattern 4: Integration Test with Real DB

```python
# tests/integration/conftest.py
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from alembic import command
from alembic.config import Config

@pytest.fixture(scope="session")
def test_db():
    """Create test database with migrations."""
    engine = create_engine("postgresql://test:test@localhost:5432/test_db")
    alembic_cfg = Config("alembic.ini")
    alembic_cfg.set_main_option("sqlalchemy.url", str(engine.url))
    command.upgrade(alembic_cfg, "head")
    yield engine
    engine.dispose()

@pytest.fixture
def session(test_db):
    """Transaction-scoped session — auto-rollback after test."""
    connection = test_db.connect()
    transaction = connection.begin()
    Session = sessionmaker(bind=connection)
    session = Session()
    yield session
    session.close()
    transaction.rollback()
    connection.close()
```

### Pattern 5: Mocking Anti-Patterns (and how to do it right)

```python
from unittest.mock import MagicMock, patch

# ❌ BAD: Overmocking — test passes but verifies nothing
@patch("myapp.service.UserRepository")
@patch("myapp.service.EmailService")
def test_create_user(mock_email, mock_repo):
    mock_repo.add.return_value = {"id": 1, "name": "Test"}
    result = create_user({"name": "Test"})
    assert result is not None  # meaningless!

# ✅ GOOD: Partial mocking — mock only external services
def test_create_user_sends_email(user_repo):
    mock_email = MagicMock()
    mock_email.send.return_value = {"message_id": "test-123"}
    service = UserService(repo=user_repo, email_service=mock_email)
    user = service.create({"name": "Test", "email": "test@test.com"})
    assert user["id"] is not None
    mock_email.send.assert_called_once_with(to="test@test.com", template="welcome")

# ❌ BAD: Mocking the thing under test
@patch("myapp.service.UserService.create")  # don't!
def test_create_user(mock_create): ...

# ✅ GOOD: Mock dependencies, not the system under test
```

## Key Pitfalls

| Mistake | Why it's bad | Fix |
|---|---|---|
| Test depends on another test | Execution order is not guaranteed | Each test must be self-contained |
| Overmocking (mock everything) | Test passes, code is broken | Mock only external deps |
| Testing private methods | Tied to implementation, not behavior | Test public API |
| `assert True` as final check | Test always passes | Use real assertions |
| `time.sleep()` in tests | Flaky, slow | Use async/await, mock time |
| Tests with side effects | Next test will break | Transaction rollback, cleanup fixtures |
| Magic numbers in assertions | Unclear what is being checked | Named constants, comments |
| Tests >50 lines | Too hard to understand | Split into multiple tests |

## Best Practices

1. **One assert per test** (or one topic) — if the test fails, the cause is clear
2. **Test behavior, not implementation** — what the code does, not how
3. **Named assertions** — `pytest.raises(ExpectedError, match="pattern")`
4. **Tests are readable as documentation** — Arrange-Act-Assert with comments
5. **Minimize mocking** — mock only external services (email, payment, API)
6. **Fast tests** — unit tests <1 second each, integration <10 seconds
7. **Deterministic tests** — do not use `datetime.now()`, `random()`, UUID without seed
8. **Test the happy path first** — then edge cases, then error paths
9. **Coverage — a tool, not a goal** — 80%+ is good, but 100% ≠ "no bugs"
10. **Flaky tests — remove immediately** — they degrade confidence in CI

## Additional Resources

- **Advanced patterns:** See [`advanced.md`](advanced.md) for property-based testing, contract testing, Testcontainers, mutation testing, test parallelization, and coverage strategies
- **Code examples:** See [`examples.md`](examples.md) for complete working examples and templates

## See also

> **See also**: `javascript-typescript-professional` — Vitest setup, TS testing patterns, React component testing.

## Context7 Integration

When Context7 MCP tools are available in your session, use them to fetch up-to-date library documentation instead of relying on memory. Tool names vary by installation (e.g. `mcp__context7__resolve-library-id` / `mcp__context7__query-docs`, or plugin-prefixed variants such as `mcp__plugin_context7_context7__*`) — check the available-tools listing for the exact names. Always resolve the library ID first; the IDs in the table below are examples and may change.

| Library | Context7 ID | When to Query |
|---------|-------------|---------------|
| pytest | `/pytest-dev/pytest` | Fixtures, plugins, configuration |
| pytest-asyncio | `/pytest-dev/pytest-asyncio` | Async test patterns |
| Hypothesis | (query "Hypothesis Python") | Property-based testing |
| Testcontainers | (query "Testcontainers") | Integration test infrastructure |
| Vitest | `/vitest-dev/vitest` | JS/TS testing |
