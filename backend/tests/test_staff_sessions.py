"""Council staff and platform admins have shorter sessions than residents."""

from collections.abc import Callable
from datetime import UTC, datetime, timedelta

from fastapi.testclient import TestClient
from sqlalchemy import Engine, text

from app.core.config import get_settings
from app.models.councils import CouncilRole
from tests.conftest import (
    add_member,
    create_council,
    csrf_headers,
    make_platform_admin,
    register,
    sign_in,
)

STAFF_IDLE = timedelta(minutes=get_settings().staff_session_idle_timeout_minutes)
STAFF_LIFETIME = timedelta(minutes=get_settings().staff_session_absolute_timeout_minutes)


def age_sessions(
    owner_engine: Engine, email: str, *, idle: timedelta | None = None, age: timedelta | None = None
) -> None:
    now = datetime.now(UTC)
    with owner_engine.begin() as connection:
        connection.execute(
            text(
                "UPDATE user_sessions SET last_seen_at = :seen, created_at = :created "
                "WHERE user_id = (SELECT id FROM users WHERE email = :email)"
            ),
            {
                "seen": now - (idle or timedelta()) - timedelta(seconds=1),
                "created": now - (age or timedelta()) - timedelta(seconds=1),
                "email": email,
            },
        )


def make_officer(make_client: Callable[[], TestClient]) -> TestClient:
    platform = make_client()
    platform_session = make_platform_admin(platform, "platform@example.com")
    council = create_council(platform, platform_session, "harare")
    officer = make_client()
    register(officer, email="officer@example.com")
    add_member(
        platform, platform_session, council["id"], "officer@example.com", CouncilRole.COUNCIL_ADMIN
    )
    return officer


def test_staff_session_ends_after_staff_idle_limit(
    make_client: Callable[[], TestClient], owner_engine: Engine
) -> None:
    officer = make_officer(make_client)
    age_sessions(owner_engine, "officer@example.com", idle=STAFF_IDLE)
    assert officer.get("/api/v1/auth/session").status_code == 401


def test_staff_session_ends_after_staff_lifetime(
    make_client: Callable[[], TestClient], owner_engine: Engine
) -> None:
    officer = make_officer(make_client)
    age_sessions(owner_engine, "officer@example.com", age=STAFF_LIFETIME)
    assert officer.get("/api/v1/auth/session").status_code == 401


def test_expired_staff_session_is_revoked(
    make_client: Callable[[], TestClient], owner_engine: Engine
) -> None:
    officer = make_officer(make_client)
    age_sessions(owner_engine, "officer@example.com", idle=STAFF_IDLE)
    officer.get("/api/v1/auth/session")
    with owner_engine.connect() as connection:
        revoked = connection.scalar(
            text(
                "SELECT revoked_at IS NOT NULL FROM user_sessions s JOIN users u "
                "ON u.id = s.user_id WHERE u.email = 'officer@example.com'"
            )
        )
    assert revoked is True


def test_resident_keeps_session_beyond_staff_limits(
    client: TestClient, owner_engine: Engine
) -> None:
    register(client, email="resident@example.com")
    age_sessions(owner_engine, "resident@example.com", idle=STAFF_IDLE, age=STAFF_LIFETIME)
    assert client.get("/api/v1/auth/session").status_code == 200


def test_platform_admin_gets_staff_limits(client: TestClient, owner_engine: Engine) -> None:
    make_platform_admin(client, "platform@example.com")
    age_sessions(owner_engine, "platform@example.com", idle=STAFF_IDLE)
    assert client.get("/api/v1/auth/session").status_code == 401


def test_former_staff_return_to_resident_limits(
    make_client: Callable[[], TestClient], owner_engine: Engine
) -> None:
    platform = make_client()
    platform_session = make_platform_admin(platform, "platform@example.com")
    council = create_council(platform, platform_session, "harare")
    register(make_client(), email="keeper@example.com")
    add_member(platform, platform_session, council["id"], "keeper@example.com", "council_admin")
    former = make_client()
    register(former, email="former@example.com")
    member = add_member(
        platform, platform_session, council["id"], "former@example.com", "maintenance_officer"
    ).json()
    platform.delete(
        f"/api/v1/councils/{council['id']}/members/{member['membership_id']}",
        headers=csrf_headers(platform_session),
    )
    sign_in(former, "former@example.com")
    age_sessions(owner_engine, "former@example.com", idle=STAFF_IDLE)
    assert former.get("/api/v1/auth/session").status_code == 200


def test_active_staff_within_limits_stay_signed_in(make_client: Callable[[], TestClient]) -> None:
    officer = make_officer(make_client)
    assert officer.get("/api/v1/auth/session").status_code == 200
