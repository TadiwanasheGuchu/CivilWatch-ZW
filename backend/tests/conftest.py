"""Shared test fixtures.

Tests run against a real PostgreSQL + PostGIS database and Redis, never
mocks of them. Point CIVICWATCH_DATABASE_URL / CIVICWATCH_REDIS_URL at
disposable test services (docker compose provides them).
"""

import os
from collections.abc import Iterator

import pytest
from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient

os.environ.setdefault("CIVICWATCH_ENVIRONMENT", "test")

from app.core.config import get_settings  # noqa: E402
from app.main import create_app  # noqa: E402

BACKEND_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


@pytest.fixture(scope="session", autouse=True)
def migrated_database() -> None:
    config = Config(os.path.join(BACKEND_ROOT, "alembic.ini"))
    config.set_main_option("script_location", os.path.join(BACKEND_ROOT, "alembic"))
    command.upgrade(config, "head")


@pytest.fixture
def client() -> Iterator[TestClient]:
    app = create_app(get_settings())
    with TestClient(app) as test_client:
        yield test_client
