from fastapi.testclient import TestClient

from app.core.config import Settings
from app.main import create_app


def test_docs_disabled_in_production() -> None:
    app = create_app(Settings(environment="production"))
    with TestClient(app) as client:
        assert client.get("/docs").status_code == 404
        assert client.get("/api/v1/openapi.json").status_code == 404
