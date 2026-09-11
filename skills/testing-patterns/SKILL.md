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
from sqlalchemy.orm import sessionmaker


# --- Test doubles (canonical API — used consistently across all patterns) ---

class FakeUserRepository:
    """In-memory test double.  API mirrors database-patterns repository
    (add / get / list / delete) but is synchronous for unit tests."""

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

    def exists_by_email(self, email: str) -> bool:
        return any(u["email"] == email for u in self._store.values())


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

    async def create_async(self, data: dict) -> dict:
        return self.create(data)


# --- Fixtures ---

@pytest.fixture
def user_repo():
    """Fresh in-memory repository per test."""
    return FakeUserRepository()


@pytest.fixture
def user_data():
    """Base user data for tests (password meets the min-12 policy)."""
    return {
        "name": "Test User",
        "email": "test@example.com",
        "password": "correct-horse-battery",
    }


@pytest.fixture
def db_session(db_engine):
    """Create isolated DB session for each test (transaction-scoped)."""
    connection = db_engine.connect()
    transaction = connection.begin()
    Session = sessionmaker(bind=connection)
    session = Session()

    yield session

    session.close()
    transaction.rollback()  # Clean up — no residue
    connection.close()


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


# test_user_service.py
def test_create_user(user_service, user_data):
    # Arrange
    email_svc = user_service.email_service

    # Act
    user = user_service.create(user_data)

    # Assert
    assert user["name"] == "Test User"
    email_svc.send.assert_called_once()  # verify side effect
```

### Pattern 2: Parametrized Tests

```python
import pytest

# Password POLICY (canonical: secure-coding-patterns, NIST SP 800-63B):
# min length 12, NO composition rules, breach-list check recommended.
@pytest.mark.parametrize("password,expected_error", [
    ("short", "at least 12 characters"),
    ("Secure123!", "at least 12 characters"),    # composition doesn't compensate for length
    ("correct-horse-battery", None),             # 12+ chars — valid, no composition required
    ("password123456789", "known breach data"),  # long but breached — reject (matches secure-coding-patterns: "Password appears in known breach data — choose another")
])
def test_password_validation(password, expected_error):
    if expected_error:
        with pytest.raises(ValueError, match=expected_error):
            validate_password(password)
    else:
        result = validate_password(password)
        assert result is True

@pytest.mark.parametrize("endpoint,method", [
    ("/api/users", "GET"),
    ("/api/users/1", "GET"),
    ("/api/users", "POST"),
    ("/api/orders", "GET"),
])
def test_endpoints_require_auth(client, endpoint, method):
    """Verify all endpoints require authentication."""
    response = getattr(client, method.lower())(endpoint)
    assert response.status_code == 401
```

### Pattern 3: Async Test Patterns

```python
import pytest
from unittest.mock import AsyncMock, patch

@pytest.mark.asyncio
async def test_async_user_creation(user_service, user_data):
    # Arrange
    expected_email = user_data["email"]

    # Act
    user = await user_service.create_async(user_data)

    # Assert
    assert user["email"] == expected_email
    assert user["id"] is not None

@pytest.mark.asyncio
async def test_service_handles_external_failure():
    """Service should handle external service failures gracefully."""
    # Arrange — mock that fails
    mock_payment = AsyncMock()
    mock_payment.process.side_effect = ConnectionError("Payment gateway down")

    service = OrderService(payment_service=mock_payment)
    order_data = {"items": [{"id": 1, "qty": 2}], "total": 29.99}

    # Act & Assert
    with pytest.raises(ServiceError, match="Payment unavailable"):
        await service.create_order(order_data)

    mock_payment.process.assert_called_once()
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

    # Run migrations
    alembic_cfg = Config("alembic.ini")
    alembic_cfg.set_main_option("sqlalchemy.url", str(engine.url))
    command.upgrade(alembic_cfg, "head")

    yield engine

    # Cleanup
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

# tests/integration/test_user_repository.py
def test_repository_crud():
    """Full integration test — uses FakeUserRepository (same API as
    database-patterns: add / get / list / delete).  Swap in a real
    repository backed by the `session` fixture for true DB integration."""
    repo = FakeUserRepository()

    # Create (add)
    user = repo.add({"name": "Test", "email": "test@test.com"})
    assert user["id"] is not None

    # Read (get)
    found = repo.get(user["id"])
    assert found["name"] == "Test"

    # List
    all_users = repo.list()
    assert len(all_users) == 1

    # Delete
    assert repo.delete(user["id"]) is True
    assert repo.get(user["id"]) is None
```

### Pattern 5: Mocking Anti-Patterns (and how to do it right)

```python
from unittest.mock import MagicMock, patch

# ❌ BAD: Overmocking — test passes but verifies nothing
@patch("myapp.service.UserRepository")
@patch("myapp.service.EmailService")
@patch("myapp.service.AuditService")
def test_create_user(mock_audit, mock_email, mock_repo):
    mock_repo.add.return_value = {"id": 1, "name": "Test"}
    mock_email.send.return_value = {"id": "123"}

    result = create_user({"name": "Test"})  # no real assertions!
    assert result is not None  # meaningless assertion


# ✅ GOOD: Partial mocking — mock only external services
def test_create_user_sends_email(user_repo):
    """Verify user creation triggers email notification."""
    mock_email = MagicMock()
    mock_email.send.return_value = {"message_id": "test-123"}

    service = UserService(repo=user_repo, email_service=mock_email)
    user = service.create({"name": "Test", "email": "test@test.com"})

    # Assert real behavior
    assert user["id"] is not None
    assert user["email"] == "test@test.com"
    mock_email.send.assert_called_once_with(
        to="test@test.com",
        template="welcome"
    )


# ❌ BAD: Mocking the thing under test
@patch("myapp.service.UserService.create")  # don't mock what you're testing!
def test_create_user(mock_create):
    ...


# ✅ GOOD: Mock dependencies, not the system under test
def test_create_user_calls_repository(user_repo):
    service = UserService(repo=user_repo)  # real repo (FakeUserRepository)
    user = service.create({"name": "Test"})

    # Verify the result through the real repository
    found = user_repo.get(user["id"])
    assert found is not None
```

### Pattern 6: Test Coverage Strategy

```bash
# pytest + coverage
pytest tests/ \
    --cov=myapp \
    --cov-report=html \
    --cov-report=term-missing \
    --cov-fail-under=80 \
    --cov-branch
```

```toml
# Coverage configuration in pyproject.toml
[tool.coverage.run]
source = ["myapp"]
omit = [
    "tests/*",
    "*/migrations/*",
    "*/conftest.py",
]
branch = true

[tool.coverage.report]
exclude_lines = [
    "pragma: no cover",
    "if TYPE_CHECKING:",
    "def __repr__",
    "raise NotImplementedError",
]
fail_under = 80
show_missing = true
```

### Pattern 7: Testing Error Handling

```python
def test_service_raises_on_invalid_input(user_repo):
    """Verify proper error handling for bad input."""
    service = UserService(repo=user_repo)

    with pytest.raises(ValidationError) as exc_info:
        service.create({"name": "", "email": "not-an-email"})

    assert "email" in str(exc_info.value)

def test_service_no_partial_data_on_failure(user_repo):
    """Verify no partial data when email service fails after create."""
    mock_email = AsyncMock()
    mock_email.send.side_effect = ConnectionError("SMTP down")
    service = UserService(repo=user_repo, email_service=mock_email)

    with pytest.raises(ServiceError):
        service.create({"name": "Test", "email": "test@test.com"})

    # Verify no partial data — repo is empty because the service
    # should not leave orphaned records when a side-effect fails.
    assert user_repo.list() == []
```

### Pattern 8: Property-Based Testing (Hypothesis)

```python
from hypothesis import given, strategies as st
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

def make_test_session():
    """Self-contained DB setup, safe to call for EVERY generated example."""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine)()

@given(
    name=st.text(min_size=1, max_size=100),
    email=st.emails()
)
def test_user_creation_always_succeeds(name, email):
    """Property: any valid name + email should create user.

    Note: @given CANNOT be combined with function-scoped pytest fixtures —
    a fixture runs once per test function, not once per generated example,
    so Hypothesis raises HealthCheck.function_scoped_fixture. Set up
    resources inside the test (as here) or use module-scoped fixtures.
    """
    repo = FakeUserRepository()
    service = UserService(repo=repo)
    user = service.create({"name": name, "email": email})

    assert user["name"] == name
    assert user["email"] == email
    assert user["id"] is not None

@given(page_size=st.integers(min_value=1, max_value=100))
def test_pagination_never_returns_more_than_page_size(page_size):
    """Property: pagination always respects page_size and returns
    disjoint pages — the generated value is the one being asserted on."""
    repo = FakeUserRepository()
    # Insert page_size + k rows so the assertion is non-vacuous
    total_rows = page_size + min(page_size, 5)
    for i in range(total_rows):
        repo.add({"name": f"User {i}", "email": f"user{i}@test.com"})

    page1 = repo.list(offset=0, limit=page_size)
    page2 = repo.list(offset=page_size, limit=page_size)

    assert len(page1) <= page_size
    assert len(page2) <= page_size
    # Pages must be disjoint (no overlapping IDs)
    ids1 = {u["id"] for u in page1}
    ids2 = {u["id"] for u in page2}
    assert ids1.isdisjoint(ids2)
```

> **See also**: `javascript-typescript-professional` — Vitest setup, TS testing patterns, React component testing.

### Contract Testing (Pact)
```python
# Consumer test — defines expected interaction (pact-python 3.x API)
from collections.abc import Generator
from pathlib import Path

import pytest
from pact import Pact, match


@pytest.fixture
def pact() -> Generator[Pact, None, None]:
    """Set up a Pact mock provider for consumer tests."""
    pact = Pact("UserService", "AuthServer").with_specification("V4")
    yield pact
    pact.write_file(Path(__file__).parent / "pacts")


def test_auth_login(pact: Pact) -> None:
    # Methods before will_respond_with() configure the REQUEST,
    # methods after it configure the RESPONSE
    (
        pact
        .upon_receiving("a request to authenticate alice")
        .given("user alice exists")
        .with_request("POST", "/auth/login")
        .with_body(
            {"email": "alice@example.com", "password": "correct-horse-battery"},
            content_type="application/json",
        )
        .will_respond_with(200)
        .with_body(
            {"token": match.str("eyJhbG..."), "expires_in": match.int(3600)},
            content_type="application/json",
        )
    )

    # Consumer code under test, against the Pact mock server
    with pact.serve() as srv:
        auth_client = AuthClient(base_url=str(srv.url))
        result = auth_client.login("alice@example.com", "correct-horse-battery")
        assert result["expires_in"] == 3600
```

> **Version caveat**: pact-python ≤ 1.x used `pact.Consumer(...).has_pact_with(pact.Provider(...))` with lowercase `pact.like(...)`; the legacy v2 API lives under `pact.v2` (capitalized matchers: `from pact.v2.matchers import Like`). Current 3.x uses the single `Pact` class and `from pact import match` as shown above — see the project's MIGRATION.md.

### Testcontainers for Integration Tests
```python
# conftest.py — real PostgreSQL in Docker
import pytest
from testcontainers.postgres import PostgresContainer
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker  # async context: use async_sessionmaker

@pytest.fixture(scope="session")
def postgres_container():
    with PostgresContainer("postgres:17-alpine") as pg:
        yield pg

@pytest.fixture(scope="session")
def db_engine(postgres_container):
    url = postgres_container.get_connection_url()
    engine = create_engine(url)
    # Run migrations
    from alembic.config import Config
    from alembic import command
    alembic_cfg = Config("alembic.ini")
    alembic_cfg.set_main_option("sqlalchemy.url", url)
    command.upgrade(alembic_cfg, "head")
    yield engine
    engine.dispose()

@pytest.fixture
def db_session(db_engine):
    """Transaction-scoped session — auto-rollback after test.

    Uses an outer transaction so that tests can call commit() freely
    without leaking data — the outer transaction is rolled back on
    teardown, discarding all commits (same recipe as Pattern 1).
    """
    connection = db_engine.connect()
    transaction = connection.begin()
    Session = sessionmaker(bind=connection)
    session = Session()

    yield session

    session.close()
    transaction.rollback()
    connection.close()

def test_create_user(db_session):
    user = User(email="test@example.com", name="Test")
    db_session.add(user)
    db_session.commit()
    assert user.id is not None
```

### Mutation Testing (mutmut)
```bash
# Install and run mutation testing (mutmut 3.x — always pytest-driven)
pip install mutmut
mutmut run

# Check results (lists surviving mutants by default; --all includes killed)
mutmut results

# Interactive terminal UI to review mutants
mutmut browse

# Show/apply a specific mutant by name (mutant names come from `results`/`browse`)
mutmut show <mutant_name>
mutmut apply <mutant_name>
```

```toml
# mutmut 3.x configuration in pyproject.toml
[tool.mutmut]
source_paths = ["src/"]                          # renamed from paths_to_mutate (deprecated)
pytest_add_cli_args_test_selection = ["tests/"]  # args that select/deselect tests
# pytest_add_cli_args = ["-p", "no:some_plugin"] # other pytest CLI args
```

> **Version caveat**: mutmut ≤ 2.x used `mutmut run --paths-to-mutate=src/`, `mutmut show --all`, and `[tool.mutmut] paths_to_mutate / tests_dir / runner`. In 3.x those CLI flags and the `runner` option are gone — mutmut drives pytest itself.

### Test Parallelization (pytest-xdist)
```bash
# Run tests in parallel across 4 workers
pytest -n 4

# Auto-detect optimal worker count
pytest -n auto

# With coverage (combine results)
pytest -n auto --cov=src --cov-report=term-missing
```

```python
# conftest.py — ensure test isolation for parallel execution (pytest-xdist)
import pytest
from sqlalchemy import event, text

# Fallback worker_id when pytest-xdist is not installed — xdist provides
# its own worker_id fixture ("gw0", "gw1", …) only when running with -n.
try:
    import xdist  # noqa: F401
except ImportError:
    @pytest.fixture(scope="session")
    def worker_id():
        """Fallback when pytest-xdist is not installed."""
        return "master"


@pytest.fixture(scope="session", autouse=True)
def worker_schema(db_engine, worker_id):
    """Each xdist worker gets its own Postgres schema to avoid conflicts.

    search_path is PER-CONNECTION: running SET on one pooled connection
    that goes back to the pool before the test runs isolates nothing —
    the test's session uses a different connection. Instead, apply it to
    EVERY DBAPI connection the engine opens via a "connect" event listener.
    Create the tables inside the worker schema too (e.g. re-run migrations
    once the listener below is active, or use schema-qualified metadata) —
    an empty schema isolates nothing.
    """
    suffix = "main" if worker_id == "master" else worker_id
    schema_name = f"test_{suffix}"

    with db_engine.connect() as conn:
        conn.execute(text(f'CREATE SCHEMA IF NOT EXISTS "{schema_name}"'))
        conn.commit()

    @event.listens_for(db_engine, "connect")
    def _set_search_path(dbapi_conn, _record):
        cursor = dbapi_conn.cursor()
        cursor.execute(f'SET search_path TO "{schema_name}"')
        cursor.close()

    # IMPORTANT: dispose pooled connections immediately after registering
    # the listener.  Pre-existing pooled connections were created BEFORE
    # the listener was attached — they still use the default search_path
    # and would leak across workers.  dispose() forces all future
    # connections to go through the "connect" event.
    db_engine.dispose()

    yield schema_name

    with db_engine.connect() as conn:
        conn.execute(text(f'DROP SCHEMA IF EXISTS "{schema_name}" CASCADE'))
        conn.commit()
```

## Best Practices

1. **One assert per test** (or one topic) — if the test fails, the cause is clear
2. **Test behavior, not implementation** — what the code does, not how
3. **Named assertions** — `pytest.raises(ExpectedError, match="pattern")`
4. **Tests are readable as documentation** — Arrange-Act-Assert with comments
5. **Minimize mocking** — mock only external services (email, payment, API)
6. **Fast tests** — unit tests <1 second each, integration <10 seconds
7. **Deterministic tests** — do not use `datetime.now()`, `random()`, UUID without seed
8. **Test the happy path first** — then edge cases, then error paths
9. **Coverage — a tool, not a goal** — 80%+ is good, but 100% does not mean "no bugs"
10. **Flaky tests — remove immediately** — they degrade confidence in CI

## Common Pitfalls

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

## Context7 Integration

When Context7 MCP tools are available in your session, use them to fetch up-to-date library documentation instead of relying on memory. Tool names vary by installation (e.g. `mcp__context7__resolve-library-id` / `mcp__context7__query-docs`, or plugin-prefixed variants such as `mcp__plugin_context7_context7__*`) — check the available-tools listing for the exact names. Always resolve the library ID first; the IDs in the table below are examples and may change.

| Library | Context7 ID | When to Query |
|---------|-------------|---------------|
| pytest | `/pytest-dev/pytest` | Fixtures, plugins, configuration |
| pytest-asyncio | `/pytest-dev/pytest-asyncio` | Async test patterns |
| Hypothesis | (query "Hypothesis Python") | Property-based testing |
| Testcontainers | (query "Testcontainers") | Integration test infrastructure |
| Vitest | `/vitest-dev/vitest` | JS/TS testing |
