"""Row-Level Security, tested directly at the database as the API's role.

These prove the database itself refuses cross-council access even if an
application query forgot its council filter.
"""

import uuid
from collections.abc import Callable, Iterator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError
from sqlalchemy.orm import Session

from app.core.database import bind_rls_user, get_session_factory
from app.models.councils import CouncilRole
from tests.conftest import add_member, create_council, make_platform_admin, register


@pytest.fixture
def world(make_client: Callable[[], TestClient]):
    platform = make_client()
    platform_session = make_platform_admin(platform, "platform@example.com")
    harare = create_council(platform, platform_session, "harare")
    bulawayo = create_council(platform, platform_session, "bulawayo")
    users = {}
    for slug, council in (("harare", harare), ("bulawayo", bulawayo)):
        email = f"admin@{slug}.example.com"
        users[slug] = register(make_client(), email=email)["user"]["id"]
        add_member(platform, platform_session, council["id"], email, CouncilRole.COUNCIL_ADMIN)
    resident = register(make_client(), email="resident@example.com")["user"]["id"]
    return {
        "harare": harare["id"],
        "bulawayo": bulawayo["id"],
        "harare_admin": users["harare"],
        "bulawayo_admin": users["bulawayo"],
        "resident": resident,
        "platform_admin": platform_session["user"]["id"],
    }


@pytest.fixture
def app_db() -> Iterator[Session]:
    with get_session_factory()() as session:
        yield session


def test_api_role_cannot_bypass_rls(app_db: Session) -> None:
    row = app_db.execute(
        text("SELECT rolsuper, rolbypassrls FROM pg_roles WHERE rolname = current_user")
    ).one()
    assert row == (False, False)
    owner = app_db.scalar(
        text("SELECT tableowner FROM pg_tables WHERE tablename = 'council_memberships'")
    )
    assert owner != app_db.scalar(text("SELECT current_user"))


def test_unauthenticated_connection_sees_no_memberships_or_audit(world, app_db: Session) -> None:
    assert app_db.scalar(text("SELECT count(*) FROM council_memberships")) == 0
    assert app_db.scalar(text("SELECT count(*) FROM audit_logs")) == 0


def test_unfiltered_query_returns_only_own_council_rows(world, app_db: Session) -> None:
    bind_rls_user(app_db, uuid.UUID(world["harare_admin"]))
    councils = app_db.scalars(
        text("SELECT DISTINCT council_id::text FROM council_memberships")
    ).all()
    assert councils == [world["harare"]]
    audit_councils = app_db.scalars(
        text("SELECT DISTINCT council_id::text FROM audit_logs WHERE council_id IS NOT NULL")
    ).all()
    assert audit_councils == [world["harare"]]


def test_resident_sees_nothing(world, app_db: Session) -> None:
    bind_rls_user(app_db, uuid.UUID(world["resident"]))
    assert app_db.scalar(text("SELECT count(*) FROM council_memberships")) == 0
    assert app_db.scalar(text("SELECT count(*) FROM audit_logs")) == 0


def test_cannot_insert_membership_into_another_council(world, app_db: Session) -> None:
    bind_rls_user(app_db, uuid.UUID(world["harare_admin"]))
    with pytest.raises(DBAPIError, match="row-level security"):
        app_db.execute(
            text(
                "INSERT INTO council_memberships (id, council_id, user_id, role) "
                "VALUES (gen_random_uuid(), :council, :user, 'council_admin')"
            ),
            {"council": world["bulawayo"], "user": world["harare_admin"]},
        )


def test_cannot_update_another_councils_memberships(world, app_db: Session) -> None:
    bind_rls_user(app_db, uuid.UUID(world["harare_admin"]))
    result = app_db.execute(
        text("UPDATE council_memberships SET role = 'maintenance_officer' WHERE council_id = :c"),
        {"c": world["bulawayo"]},
    )
    assert result.rowcount == 0


def test_audit_log_is_append_only(world, app_db: Session) -> None:
    bind_rls_user(app_db, uuid.UUID(world["platform_admin"]))
    with pytest.raises(DBAPIError, match="permission denied"):
        app_db.execute(text("UPDATE audit_logs SET action = 'tampered'"))
    app_db.rollback()
    bind_rls_user(app_db, uuid.UUID(world["platform_admin"]))
    with pytest.raises(DBAPIError, match="permission denied"):
        app_db.execute(text("DELETE FROM audit_logs"))


def test_audit_entries_cannot_impersonate_another_actor(world, app_db: Session) -> None:
    bind_rls_user(app_db, uuid.UUID(world["resident"]))
    with pytest.raises(DBAPIError, match="row-level security"):
        app_db.execute(
            text(
                "INSERT INTO audit_logs (id, occurred_at, actor_user_id, action) "
                "VALUES (gen_random_uuid(), now(), :actor, 'forged')"
            ),
            {"actor": world["harare_admin"]},
        )


def test_rls_identity_does_not_leak_between_transactions(world, app_db: Session) -> None:
    bind_rls_user(app_db, uuid.UUID(world["harare_admin"]))
    app_db.commit()
    with get_session_factory()() as other:
        # Possibly the same pooled connection: the setting was transaction-local.
        assert other.scalar(text("SELECT current_setting('app.user_id', true)")) in (None, "")
        assert other.scalar(text("SELECT count(*) FROM council_memberships")) == 0
