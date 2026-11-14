import pytest
from fastapi.testclient import TestClient
from sqlalchemy import Engine, text

from app.cli import main, set_platform_admin
from tests.conftest import register


def test_grant_and_revoke_platform_admin_are_audited(
    client: TestClient, owner_engine: Engine
) -> None:
    user_id = register(client, email="ops@example.com")["user"]["id"]
    assert main(["grant-platform-admin", "OPS@example.com"]) == 0
    assert client.get("/api/v1/users/me").json()["is_platform_admin"] is True
    assert "No change" in set_platform_admin("ops@example.com", grant=True)
    assert main(["revoke-platform-admin", "ops@example.com"]) == 0
    assert client.get("/api/v1/users/me").json()["is_platform_admin"] is False

    with owner_engine.connect() as connection:
        rows = connection.execute(
            text(
                "SELECT action, target_id::text, details->>'via' "
                "FROM audit_logs ORDER BY occurred_at"
            )
        ).all()
    assert rows == [
        ("platform_admin.granted", user_id, "cli"),
        ("platform_admin.revoked", user_id, "cli"),
    ]


def test_unknown_email_fails() -> None:
    with pytest.raises(SystemExit, match="must register first"):
        set_platform_admin("missing@example.com", grant=True)
