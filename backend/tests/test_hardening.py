"""Request size limits, HSTS, public-read and export rate limits, deployed settings."""

from collections.abc import Iterator
from datetime import UTC, datetime

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from app.core.config import Settings, get_settings
from app.main import create_app
from tests.operations_helpers import build_council


def _client(**overrides) -> TestClient:
    settings = get_settings().model_copy(update=overrides)
    app = create_app(settings)
    app.dependency_overrides[get_settings] = lambda: settings
    return TestClient(app, base_url="https://testserver")


# --- Request size ------------------------------------------------------------------


def test_oversized_json_is_refused_before_reaching_the_handler(client: TestClient) -> None:
    body = b'{"email": "' + b"a" * (2 * 1024 * 1024) + b'"}'
    response = client.post(
        "/api/v1/auth/login", content=body, headers={"Content-Type": "application/json"}
    )
    assert response.status_code == 413
    assert response.json()["error"]["code"] == "request_too_large"


def test_oversized_chunked_body_without_length_is_refused(client: TestClient) -> None:
    def chunks() -> Iterator[bytes]:
        for _ in range(40):
            yield b"x" * 64 * 1024

    response = client.post(
        "/api/v1/auth/login", content=chunks(), headers={"Content-Type": "application/json"}
    )
    assert response.status_code == 413


def test_photo_uploads_have_their_own_larger_limit(client: TestClient) -> None:
    # 3 MB is over the JSON limit but under the photo limit: it reaches the
    # handler, which needs a signed-in user.
    files = {"file": ("p.jpg", b"\xff" * (3 * 1024 * 1024), "image/jpeg")}
    response = client.post(
        "/api/v1/issues/00000000-0000-0000-0000-000000000000/photos", files=files
    )
    assert response.status_code == 401
    huge = {"file": ("p.jpg", b"\xff" * (12 * 1024 * 1024), "image/jpeg")}
    response = client.post("/api/v1/issues/00000000-0000-0000-0000-000000000000/photos", files=huge)
    assert response.status_code == 413


# --- Headers -------------------------------------------------------------------------


def test_hsts_only_when_deployed() -> None:
    with _client() as dev:
        assert "Strict-Transport-Security" not in dev.get("/api/v1/health/live").headers
    deployed = Settings(
        environment="staging",
        cors_origins=["https://civicwatch.example.org"],
        public_web_url="https://civicwatch.example.org",
        storage_access_key_id="k",
        storage_secret_access_key="s",
        migration_database_url="postgresql+psycopg://owner:pw@localhost:5432/civicwatch_test",
    )
    with TestClient(create_app(deployed), base_url="https://testserver") as client:
        hsts = client.get("/api/v1/health/live").headers["Strict-Transport-Security"]
        assert "max-age=63072000" in hsts


# --- Rate limits -----------------------------------------------------------------------


@pytest.mark.parametrize(
    "path",
    [
        "/api/v1/map/clusters?bbox=30.9,-17.95,31.2,-17.7&zoom=12",
        "/api/v1/issues/nearby?latitude=-17.83&longitude=31.05",
        "/api/v1/councils/locate?latitude=-17.83&longitude=31.05",
        "/api/v1/analytics/public",
        "/api/v1/issues",
    ],
)
def test_expensive_public_reads_are_limited_per_ip(path: str) -> None:
    with _client(public_reads_per_ip=3) as client:
        for _ in range(3):
            assert client.get(path).status_code == 200
        limited = client.get(path)
        assert limited.status_code == 429
        assert int(limited.headers["Retry-After"]) > 0


def test_exports_are_limited_per_user(make_client) -> None:
    c = build_council(make_client)
    settings = get_settings().model_copy(update={"exports_per_user": 2})
    c["admin"].client.app.dependency_overrides[get_settings] = lambda: settings
    today = datetime.now(UTC).date()
    url = f"{c['base']}/reports/export?from={today}&to={today}"
    assert [c["admin"].get(url).status_code for _ in range(3)] == [200, 200, 429]


# --- Deployed settings -------------------------------------------------------------------

_DEPLOYED = {
    "environment": "production",
    "cors_origins": ["https://civicwatch.example.org"],
    "public_web_url": "https://civicwatch.example.org",
    "storage_access_key_id": "k",
    "storage_secret_access_key": "s",
    "migration_database_url": "postgresql+psycopg://owner:pw@db:5432/civicwatch",
}


def test_valid_deployed_settings_are_accepted() -> None:
    Settings(**_DEPLOYED)


@pytest.mark.parametrize(
    ("override", "message"),
    [
        ({"cors_origins": ["http://civicwatch.example.org"]}, "cors_origins"),
        ({"public_web_url": "http://civicwatch.example.org"}, "public_web_url"),
        ({"storage_access_key_id": None}, "storage credentials"),
        ({"migration_database_url": None}, "migration_database_url"),
        (
            {
                "smtp_host": "smtp.example.org",
                "email_from": "a@example.org",
                "worker_database_url": None,
            },
            "worker_database_url",
        ),
        (
            {
                "smtp_host": "smtp.example.org",
                "email_from": "a@example.org",
                "worker_database_url": "postgresql+psycopg://w:pw@db:5432/civicwatch",
                "smtp_starttls": False,
            },
            "STARTTLS",
        ),
    ],
)
def test_unsafe_deployed_settings_are_refused(override, message) -> None:
    with pytest.raises(ValidationError, match=message):
        Settings(**{**_DEPLOYED, **override})
