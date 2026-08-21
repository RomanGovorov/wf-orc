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
# conftest.py — shared fixtures
import pytest
from unittest.mock import AsyncMock

@pytest.fixture
def user_data():
    """Base user data for tests."""
    return {
        "name": "Test User",
        "email": "test@example.com",
        "password": "Secure123!"
    }

@pytest.fixture
def db_session(db_engine):
    """Create isolated DB session for each test."""
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
def user_service(db_session, mock_email_service):
    """Service with mocked dependencies."""
    return UserService(
        db=db_session,
        email_service=mock_email_service
    )

# test_user_service.py
def test_create_user(user_service, user_data):
    # Arrange
    email_svc = user_service.email_service

    # Act
    user = user_service.create(user_data)

    # Assert
    assert user.name == "Test User"
    email_svc.send.assert_called_once()  # verify side effect
```

### Pattern 2: Parametrized Tests

```python
import pytest

@pytest.mark.parametrize("password,expected_error", [
    ("short", "at least 8 characters"),
    ("nouppercase1", "one uppercase letter"),
    ("NOLOWERCASE1", "one lowercase letter"),
    ("NoDigitsHere", "one digit"),
    ("Valid123!", None),  # should pass
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
    assert user.email == expected_email
    assert user.id is not None

@pytest.mark.asyncio
async def test_service_handles_external_failure():
    """Service should handle external service failures gracefully."""
    # Arrange — mock that fails
    mock_payment = AsyncMock()
    mock_payment.process.side_effect = ConnectionError("Payment gateway down")

    service = OrderService(payment_service=mock_payment)

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
def test_repository_crud(session):
    """Full integration test with real DB."""
    repo = UserRepository(session)

    # Create
    user = repo.create(UserCreate(name="Test", email="test@test.com"))
    assert user.id is not None

    # Read
    found = repo.get_by_id(user.id)
    assert found.name == "Test"

    # Update
    repo.update(user.id, name="Updated")
    updated = repo.get_by_id(user.id)
    assert updated.name == "Updated"

    # Delete
    repo.delete(user.id)
    assert repo.get_by_id(user.id) is None
```

### Pattern 5: Mocking Anti-Patterns (and how to do it right)

```python
# ❌ BAD: Overmocking — test passes but verifies nothing
@patch("myapp.service.UserRepository")
@patch("myapp.service.EmailService")
@patch("myapp.service.AuditService")
def test_create_user(mock_audit, mock_email, mock_repo):
    mock_repo.create.return_value = User(id=1, name="Test")
    mock_email.send.return_value = {"id": "123"}

    result = create_user({"name": "Test"})  # no real assertions!
    assert result is not None  # meaningless assertion


# ✅ GOOD: Partial mocking — mock only external services
@patch("myapp.services.email.EmailService.send")
def test_create_user_sends_email(mock_send, db_session):
    """Verify user creation triggers email notification."""
    mock_send.return_value = {"message_id": "test-123"}

    service = UserService(db=db_session)
    user = service.create({"name": "Test", "email": "test@test.com"})

    # Assert real behavior
    assert user.id is not None
    assert user.email == "test@test.com"
    mock_send.assert_called_once_with(
        to="test@test.com",
        template="welcome"
    )


# ❌ BAD: Mocking the thing under test
@patch("myapp.service.UserService.create")  # don't mock what you're testing!
def test_create_user(mock_create):
    ...


# ✅ GOOD: Mock dependencies, not the system under test
def test_create_user_calls_repository(db_session):
    repo = UserRepository(db_session)  # real repo, with test DB

    service = UserService(repo)
    user = service.create_user({"name": "Test"})

    # Verify the result through the real repository
    found = repo.get_by_id(user.id)
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
def test_service_raises_on_invalid_input():
    """Verify proper error handling for bad input."""
    service = UserService(db_session)

    with pytest.raises(ValidationError) as exc_info:
        service.create({"name": "", "email": "not-an-email"})

    assert "email" in str(exc_info.value)

def test_service_rollback_on_failure(db_session):
    """Verify DB rollback when email service fails."""
    with patch.object(EmailService, "send", side_effect=ConnectionError):
        with pytest.raises(ServiceError):
            UserService(db_session).create(user_data)

    # Verify no partial data — transaction rolled back
    from sqlalchemy import select
    stmt = select(User).where(User.email == "test@test.com")
    user = db_session.scalar(stmt)
    assert user is None
```

### Pattern 8: Property-Based Testing (Hypothesis)

```python
from hypothesis import given, strategies as st

@given(
    name=st.text(min_size=1, max_size=100),
    email=st.emails()
)
def test_user_creation_always_succeeds(name, email):
    """Property: any valid name + email should create user."""
    service = UserService(db_session)
    user = service.create({"name": name, "email": email})

    assert user.name == name
    assert user.email == email
    assert user.id is not None

@given(st.integers())
def test_pagination_never_returns_more_than_page_size(user_id):
    """Property: pagination always respects page_size."""
    results = repo.list_users(page=1, page_size=20)
    assert len(results) <= 20
```

> **See also**: `javascript-typescript-professional` — Vitest setup, TS testing patterns, React component testing.

### Contract Testing (Pact)
```python
# Consumer test — defines expected interaction
import pact

with pact.Consumer('UserService').has_pact_with(pact.Provider('AuthServer')) as p:
    (p.given('user alice exists')
     .upon_receiving('a request to authenticate alice')
     .with_request('POST', '/auth/login',
                   body={'email': 'alice@example.com', 'password': 'secret123'},
                   headers={'Content-Type': 'application/json'})
     .will_respond_with(200,
                        body={'token': pact.like('eyJhbG...'), 'expires_in': 3600},
                        headers={'Content-Type': 'application/json'}))

    # Consumer code under test
    auth_client = AuthClient(base_url=p.uri)
    result = auth_client.login('alice@example.com', 'secret123')
    assert result['expires_in'] == 3600
```

### Testcontainers for Integration Tests
```python
# conftest.py — real PostgreSQL in Docker
import pytest
from testcontainers.postgres import PostgresContainer
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

@pytest.fixture(scope="session")
def postgres_container():
    with PostgresContainer("postgres:16-alpine") as pg:
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
    Session = sessionmaker(bind=db_engine)
    session = Session()
    yield session
    session.rollback()
    session.close()

def test_create_user(db_session):
    user = User(email="test@example.com", name="Test")
    db_session.add(user)
    db_session.commit()
    assert user.id is not None
```

### Mutation Testing (mutmut)
```bash
# Install and run mutation testing
pip install mutmut
mutmut run --paths-to-mutate=src/

# Check results
mutmut results

# Show survived mutants for review
mutmut show --all
```

```python
# mutmut configuration in pyproject.toml
# [tool.mutmut]
# paths_to_mutate = "src/"
# tests_dir = "tests/"
# runner = "python -m pytest tests/ -x --timeout=30"
```

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
# conftest.py — ensure test isolation for parallel execution
import pytest
import uuid
from sqlalchemy import text

@pytest.fixture(autouse=True)
def unique_schema(db_engine):
    """Each worker gets its own schema to avoid conflicts."""
    schema_name = f"test_{uuid.uuid4().hex[:8]}"
    with db_engine.connect() as conn:
        conn.execute(text(f"CREATE SCHEMA {schema_name}"))
        conn.execute(text(f"SET search_path TO {schema_name}"))
        conn.commit()
    yield schema_name
    with db_engine.connect() as conn:
        conn.execute(text(f"DROP SCHEMA {schema_name} CASCADE"))
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

When working with testing patterns, verify against current documentation:

| Library | Context7 ID | When to Query |
|---------|-------------|---------------|
| pytest | `/pytest-dev/pytest` | Fixtures, plugins, configuration |
| pytest-asyncio | `/pytest-dev/pytest-asyncio` | Async test patterns |
| Hypothesis | (query "Hypothesis Python") | Property-based testing |
| Testcontainers | (query "Testcontainers") | Integration test infrastructure |
| Vitest | `/vitest-dev/vitest` | JS/TS testing |

Use `mcp__context7__resolve-library-id` then `mcp__context7__query-docs` to get current examples.
