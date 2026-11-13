from fastapi.testclient import TestClient
from redis import Redis

from app.core.cache import get_redis


def test_liveness(client: TestClient) -> None:
    response = client.get("/api/v1/health/live")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_readiness_reports_database_postgis_and_cache(client: TestClient) -> None:
    response = client.get("/api/v1/health/ready")
    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "database": "ok",
        "postgis": "ok",
        "cache": "ok",
    }


def test_readiness_degrades_when_cache_is_down(client: TestClient) -> None:
    unreachable = Redis(host="127.0.0.1", port=1, socket_connect_timeout=0.2)
    client.app.dependency_overrides[get_redis] = lambda: unreachable
    try:
        response = client.get("/api/v1/health/ready")
    finally:
        client.app.dependency_overrides.clear()
    assert response.status_code == 503
    body = response.json()
    assert body["status"] == "degraded"
    assert body["cache"] == "unavailable"
    assert body["database"] == "ok"
