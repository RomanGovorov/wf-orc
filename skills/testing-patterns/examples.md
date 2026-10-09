# Code Examples: Testing Patterns

> Working examples for [`SKILL.md`](SKILL.md).

## Example 1: Complete conftest.py with Test Doubles

```python
# conftest.py — shared fixtures and canonical test doubles
import pytest
from unittest.mock import AsyncMock
from sqlalchemy.orm import sessionmaker


# --- Test doubles ---

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
    """Base user data for tests (password meets min-12 policy)."""
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
    transaction.rollback()
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
```

## Example 2: Complete Unit Test File

```python
# test_user_service.py
import pytest
from unittest.mock import MagicMock

def test_create_user(user_service, user_data):
    """Test basic user creation."""
    user = user_service.create(user_data)
    assert user["name"] == "Test User"
    assert user["email"] == "test@example.com"
    assert user["id"] is not None
    user_service.email_service.send.assert_called_once()


def test_create_user_sends_email(user_repo):
    """Verify user creation triggers email notification."""
    mock_email = MagicMock()
    mock_email.send.return_value = {"message_id": "test-123"}
    service = UserService(repo=user_repo, email_service=mock_email)
    user = service.create({"name": "Test", "email": "test@test.com"})
    assert user["id"] is not None
    mock_email.send.assert_called_once_with(
        to="test@test.com",
        template="welcome"
    )


def test_create_user_without_email_service(user_repo, user_data):
    """Service works without email service (optional dependency)."""
    service = UserService(repo=user_repo, email_service=None)
    user = service.create(user_data)
    assert user["id"] is not None
```

## Example 3: Complete Parametrized Tests

```python
import pytest

@pytest.mark.parametrize("password,expected_error", [
    ("short", "at least 12 characters"),
    ("Secure123!", "at least 12 characters"),
    ("correct-horse-battery", None),
    ("password123456789", "known breach data"),
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

## Example 4: Complete Async Test Patterns

```python
import pytest
from unittest.mock import AsyncMock, patch

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
    order_data = {"items": [{"id": 1, "qty": 2}], "total": 29.99}

    with pytest.raises(ServiceError, match="Payment unavailable"):
        await service.create_order(order_data)

    mock_payment.process.assert_called_once()
```

## Example 5: Complete Integration Test with Real DB

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


# tests/integration/test_user_repository.py
def test_repository_crud():
    """Full integration test with FakeUserRepository."""
    repo = FakeUserRepository()

    # Create
    user = repo.add({"name": "Test", "email": "test@test.com"})
    assert user["id"] is not None

    # Read
    found = repo.get(user["id"])
    assert found["name"] == "Test"

    # List
    all_users = repo.list()
    assert len(all_users) == 1

    # Delete
    assert repo.delete(user["id"]) is True
    assert repo.get(user["id"]) is None
```

## Example 6: Complete Property-Based Testing

```python
from hypothesis import given, strategies as st

@given(
    name=st.text(min_size=1, max_size=100),
    email=st.emails()
)
def test_user_creation_always_succeeds(name, email):
    """Property: any valid name + email should create user."""
    repo = FakeUserRepository()
    service = UserService(repo=repo)
    user = service.create({"name": name, "email": email})
    assert user["name"] == name
    assert user["email"] == email
    assert user["id"] is not None


@given(page_size=st.integers(min_value=1, max_value=100))
def test_pagination_never_returns_more_than_page_size(page_size):
    """Property: pagination always respects page_size."""
    repo = FakeUserRepository()
    total_rows = page_size + min(page_size, 5)
    for i in range(total_rows):
        repo.add({"name": f"User {i}", "email": f"user{i}@test.com"})

    page1 = repo.list(offset=0, limit=page_size)
    page2 = repo.list(offset=page_size, limit=page_size)

    assert len(page1) <= page_size
    assert len(page2) <= page_size
    ids1 = {u["id"] for u in page1}
    ids2 = {u["id"] for u in page2}
    assert ids1.isdisjoint(ids2)
```

## Example 7: Complete Testcontainers Setup

```python
# conftest.py
import pytest
from testcontainers.postgres import PostgresContainer
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

@pytest.fixture(scope="session")
def postgres_container():
    with PostgresContainer("postgres:17-alpine") as pg:
        yield pg

@pytest.fixture(scope="session")
def db_engine(postgres_container):
    url = postgres_container.get_connection_url()
    engine = create_engine(url)
    from alembic.config import Config
    from alembic import command
    alembic_cfg = Config("alembic.ini")
    alembic_cfg.set_main_option("sqlalchemy.url", url)
    command.upgrade(alembic_cfg, "head")
    yield engine
    engine.dispose()

@pytest.fixture
def db_session(db_engine):
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

## Example 8: Complete Coverage Configuration

```toml
# pyproject.toml
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

```bash
# Run with coverage
pytest tests/ \
    --cov=myapp \
    --cov-report=html \
    --cov-report=term-missing \
    --cov-fail-under=80 \
    --cov-branch
```

## Example 9: Complete Mocking Patterns

```python
from unittest.mock import MagicMock, patch, AsyncMock

# ✅ GOOD: Partial mocking — mock only external services
def test_create_user_sends_email(user_repo):
    mock_email = MagicMock()
    mock_email.send.return_value = {"message_id": "test-123"}
    service = UserService(repo=user_repo, email_service=mock_email)
    user = service.create({"name": "Test", "email": "test@test.com"})
    assert user["id"] is not None
    assert user["email"] == "test@test.com"
    mock_email.send.assert_called_once_with(
        to="test@test.com",
        template="welcome"
    )


# ❌ BAD: Overmocking
@patch("myapp.service.UserRepository")
@patch("myapp.service.EmailService")
@patch("myapp.service.AuditService")
def test_create_user(mock_audit, mock_email, mock_repo):
    mock_repo.add.return_value = {"id": 1, "name": "Test"}
    result = create_user({"name": "Test"})
    assert result is not None  # meaningless!


# ✅ GOOD: Mock dependencies, not the system under test
def test_create_user_calls_repository(user_repo):
    service = UserService(repo=user_repo)
    user = service.create({"name": "Test"})
    found = user_repo.get(user["id"])
    assert found is not None
```

---

## Additional Resources

- **Core patterns:** See [`SKILL.md`](SKILL.md) for essential patterns
- **Advanced techniques:** See [`advanced.md`](advanced.md) for deep dives and edge cases
