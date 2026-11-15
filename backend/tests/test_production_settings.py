import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from app.core.config import Settings
from app.main import create_app


def test_docs_disabled_in_production() -> None:
    app = create_app(
        Settings(
            environment="production",
            cors_origins=["https://civicwatch.example.org"],
            public_web_url="https://civicwatch.example.org",
            storage_access_key_id="k",
            storage_secret_access_key="s",
            migration_database_url="postgresql+psycopg://owner:pw@localhost:5432/civicwatch",
        )
    )
    with TestClient(app) as client:
        assert client.get("/docs").status_code == 404
        assert client.get("/api/v1/openapi.json").status_code == 404


def test_production_refuses_insecure_session_cookies() -> None:
    with pytest.raises(ValidationError):
        Settings(
            environment="production",
            session_cookie_name="cw_session",
            session_cookie_secure=False,
        )


def test_host_prefixed_cookie_requires_secure_flag() -> None:
    with pytest.raises(ValidationError):
        Settings(environment="development", session_cookie_secure=False)


def test_staff_limits_cannot_exceed_resident_limits() -> None:
    with pytest.raises(ValidationError):
        Settings(staff_session_idle_timeout_minutes=60 * 24 * 365)
