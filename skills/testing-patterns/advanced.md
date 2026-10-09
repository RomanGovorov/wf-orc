# Advanced Patterns: Testing Patterns

> This file extends [`SKILL.md`](SKILL.md) with advanced patterns and edge cases.

## Test Coverage Strategy

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

## Testing Error Handling

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
    assert user_repo.list() == []  # no orphaned records
```

## Property-Based Testing (Hypothesis)

```python
from hypothesis import given, strategies as st
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

@given(
    name=st.text(min_size=1, max_size=100),
    email=st.emails()
)
def test_user_creation_always_succeeds(name, email):
    """Property: any valid name + email should create user.

    Note: @given CANNOT be combined with function-scoped pytest fixtures —
    a fixture runs once per test function, not once per generated example.
    Set up resources inside the test or use module-scoped fixtures.
    """
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
    assert ids1.isdisjoint(ids2)  # pages must be disjoint
```

## Contract Testing (Pact)

```python
# Consumer test — defines expected interaction (pact-python 3.x API)
from collections.abc import Generator
from pathlib import Path
import pytest
from pact import Pact, match

@pytest.fixture
def pact() -> Generator[Pact, None, None]:
    pact = Pact("UserService", "AuthServer").with_specification("V4")
    yield pact
    pact.write_file(Path(__file__).parent / "pacts")

def test_auth_login(pact: Pact) -> None:
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
    with pact.serve() as srv:
        auth_client = AuthClient(base_url=str(srv.url))
        result = auth_client.login("alice@example.com", "correct-horse-battery")
        assert result["expires_in"] == 3600
```

> **Version caveat**: pact-python ≤ 1.x used `pact.Consumer(...).has_pact_with(...)` with lowercase `pact.like(...)`; 3.x uses `Pact` class and `from pact import match`.

## Testcontainers for Integration Tests

```python
# conftest.py — real PostgreSQL in Docker
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
    """Transaction-scoped session — auto-rollback after test."""
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

## Mutation Testing (mutmut)

```bash
# Install and run mutation testing (mutmut 3.x)
pip install mutmut
mutmut run

# Check results
mutmut results

# Interactive terminal UI
mutmut browse

# Show/apply specific mutant
mutmut show <mutant_name>
mutmut apply <mutant_name>
```

```toml
# mutmut 3.x configuration in pyproject.toml
[tool.mutmut]
source_paths = ["src/"]
pytest_add_cli_args_test_selection = ["tests/"]
```

> **Version caveat**: mutmut ≤ 2.x used `mutmut run --paths-to-mutate=src/` and `[tool.mutmut] paths_to_mutate`. In 3.x those are gone.

## Test Parallelization (pytest-xdist)

```bash
# Run tests in parallel
pytest -n 4
pytest -n auto  # auto-detect optimal worker count

# With coverage
pytest -n auto --cov=src --cov-report=term-missing
```

```python
# conftest.py — ensure test isolation for parallel execution
import pytest
from sqlalchemy import event, text

try:
    import xdist  # noqa: F401
except ImportError:
    @pytest.fixture(scope="session")
    def worker_id():
        return "master"

@pytest.fixture(scope="session", autouse=True)
def worker_schema(db_engine, worker_id):
    """Each xdist worker gets its own Postgres schema."""
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

    # IMPORTANT: dispose pooled connections after registering listener
    db_engine.dispose()

    yield schema_name

    with db_engine.connect() as conn:
        conn.execute(text(f'DROP SCHEMA IF NOT EXISTS "{schema_name}" CASCADE'))
        conn.commit()
```

## Deep Dive: When to Use What

| Testing Type | When to Use | Tools | Speed |
|---|---|---|---|
| Unit | Pure logic, algorithms, transformations | pytest, unittest | <1ms each |
| Integration | DB queries, HTTP calls, file I/O | Testcontainers, pytest | 10-100ms each |
| Contract | Service-to-service API compatibility | Pact | 100ms-1s |
| E2E | Critical user journeys | Playwright, Cypress | 1-10s each |
| Property | Invariants, edge cases | Hypothesis | Varies |
| Mutation | Test quality assessment | mutmut | Slow |
| Performance | Latency, throughput | locust, k6 | Minutes |
| Chaos | Resilience, failure modes | Chaos Monkey, toxiproxy | Minutes |

## Edge Cases in Testing

### Hypothesis + Fixtures

`@given` cannot be combined with function-scoped pytest fixtures — a fixture runs once per test function, not once per generated example. Set up resources inside the test or use module-scoped fixtures.

### Transaction Rollback with Nested Commits

When tests call `session.commit()` freely, wrap everything in an outer transaction that gets rolled back on teardown. This discards all inner commits.

### Async Test Fixtures

For `pytest-asyncio`, use `@pytest.fixture` with `async def` and `@pytest_asyncio.fixture` (depending on version). Ensure `pytest-asyncio` mode is set to `auto` in config.

### Flaky Test Sources

- Time-dependent assertions (`datetime.now()`)
- Random data without seeds
- Network calls without mocks
- Shared mutable state between tests
- Order-dependent cleanup

---

## Additional Resources

- **Core patterns:** See [`SKILL.md`](SKILL.md) for essential patterns
- **Code examples:** See [`examples.md`](examples.md) for complete working examples
