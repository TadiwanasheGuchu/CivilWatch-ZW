"""Shared test fixtures.

Tests run against a real PostgreSQL + PostGIS database and Redis, never
mocks of them. Configure disposable test services:

- CIVICWATCH_DATABASE_URL: the unprivileged `civicwatch_app` role (as the API
  uses in production, so Row-Level Security is exercised for real);
- CIVICWATCH_MIGRATION_DATABASE_URL: the schema owner (migrations, cleanup);
- CIVICWATCH_REDIS_URL;
- photo storage: set CIVICWATCH_TEST_EXTERNAL_STORAGE=1 and the
  CIVICWATCH_STORAGE_* variables to use a real S3-compatible service
  (CI uses MinIO). Otherwise a local moto S3 emulator is started. Tests that
  prove the storage itself refuses unsigned or expired requests need a real
  service and also CIVICWATCH_TEST_STORAGE_ENFORCES_AUTH=1.

Every test truncates application tables and flushes the Redis database.
"""

import os
from collections.abc import Callable, Iterator
from typing import Any

import pytest
from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient
from sqlalchemy import Engine, create_engine, text
from sqlalchemy.orm import Session

os.environ.setdefault("CIVICWATCH_ENVIRONMENT", "test")


def _start_local_storage() -> None:
    """Run a moto S3 server for this test session and point the app at it."""
    import socket

    from moto.server import ThreadedMotoServer

    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        port = sock.getsockname()[1]
    ThreadedMotoServer(ip_address="127.0.0.1", port=port, verbose=False).start()
    endpoint = f"http://127.0.0.1:{port}"
    os.environ["CIVICWATCH_STORAGE_ENDPOINT_URL"] = endpoint
    os.environ["CIVICWATCH_STORAGE_PUBLIC_ENDPOINT_URL"] = endpoint
    os.environ["CIVICWATCH_STORAGE_ACCESS_KEY_ID"] = "test-access-key"
    os.environ["CIVICWATCH_STORAGE_SECRET_ACCESS_KEY"] = "test-secret-key"


if os.environ.get("CIVICWATCH_TEST_EXTERNAL_STORAGE") != "1":
    _start_local_storage()

from app.core.cache import get_redis  # noqa: E402
from app.core.config import get_settings  # noqa: E402
from app.core.database import get_session_factory  # noqa: E402
from app.core.storage import get_storage  # noqa: E402
from app.main import create_app  # noqa: E402
from app.models.councils import CouncilRole  # noqa: E402

BACKEND_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_PASSWORD = "correct horse battery"


@pytest.fixture(scope="session", autouse=True)
def migrated_database() -> None:
    if get_settings().environment != "test":
        raise RuntimeError("Refusing to run tests outside CIVICWATCH_ENVIRONMENT=test")
    config = Config(os.path.join(BACKEND_ROOT, "alembic.ini"))
    config.set_main_option("script_location", os.path.join(BACKEND_ROOT, "alembic"))
    command.upgrade(config, "head")
    get_storage().ensure_bucket()


@pytest.fixture(scope="session")
def owner_engine() -> Iterator[Engine]:
    engine = create_engine(get_settings().effective_migration_database_url)
    yield engine
    engine.dispose()


@pytest.fixture(autouse=True)
def clean_state(owner_engine: Engine) -> Iterator[None]:
    yield
    with owner_engine.begin() as connection:
        connection.execute(
            text(
                "TRUNCATE issue_media, issue_status_history, issues, audit_logs, "
                "council_memberships, councils, user_sessions, users "
                "RESTART IDENTITY CASCADE"
            )
        )
    get_redis().flushdb()


@pytest.fixture
def db() -> Iterator[Session]:
    with get_session_factory()() as session:
        yield session


@pytest.fixture
def client() -> Iterator[TestClient]:
    app = create_app(get_settings())
    # HTTPS base URL so Secure cookies are sent back, as in production.
    with TestClient(app, base_url="https://testserver") as test_client:
        yield test_client


@pytest.fixture
def make_client() -> Iterator[Callable[[], TestClient]]:
    """Independent clients (separate cookie jars) — i.e. separate browsers."""
    clients: list[TestClient] = []

    def factory() -> TestClient:
        test_client = TestClient(create_app(get_settings()), base_url="https://testserver")
        clients.append(test_client)
        return test_client

    yield factory
    for test_client in clients:
        test_client.close()


def register(
    client: TestClient,
    email: str = "tendai@example.com",
    password: str = DEFAULT_PASSWORD,
    full_name: str = "Tendai Moyo",
) -> dict[str, Any]:
    response = client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": password, "full_name": full_name},
    )
    assert response.status_code == 201, response.text
    return response.json()


def csrf_headers(session_body: dict[str, Any]) -> dict[str, str]:
    return {"X-CSRF-Token": session_body["csrf_token"]}


def sign_in(client: TestClient, email: str, password: str = DEFAULT_PASSWORD) -> dict[str, Any]:
    response = client.post("/api/v1/auth/login", json={"email": email, "password": password})
    assert response.status_code == 200, response.text
    return response.json()


def make_platform_admin(client: TestClient, email: str) -> dict[str, Any]:
    """Register a user, grant platform admin through the operator CLI, sign in."""
    from app.cli import set_platform_admin

    register(client, email=email, full_name="Platform Admin")
    set_platform_admin(email, grant=True)
    return sign_in(client, email)


def create_council(
    client: TestClient, admin_session: dict[str, Any], slug: str, name: str | None = None
) -> dict[str, Any]:
    response = client.post(
        "/api/v1/councils",
        json={"slug": slug, "name": name or slug.title()},
        headers=csrf_headers(admin_session),
    )
    assert response.status_code == 201, response.text
    return response.json()


def add_member(
    client: TestClient,
    session_body: dict[str, Any],
    council_id: str,
    email: str,
    role: CouncilRole | str,
) -> Any:
    return client.post(
        f"/api/v1/councils/{council_id}/members",
        json={"email": email, "role": str(role)},
        headers=csrf_headers(session_body),
    )
