"""Report visibility enforced by PostgreSQL itself, as the API's role."""

import uuid
from collections.abc import Callable, Iterator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError
from sqlalchemy.orm import Session

from app.core.database import bind_rls_user, get_session_factory
from app.models.councils import CouncilRole
from tests.conftest import add_member
from tests.issue_helpers import (
    BULAWAYO,
    new_resident,
    report_payload,
    set_status,
    setup_councils,
    submit,
)


@pytest.fixture
def world(make_client: Callable[[], TestClient], owner_engine):
    w = setup_councils(make_client)
    alice, alice_session = new_resident(make_client, "alice@example.com")
    bob, bob_session = new_resident(make_client, "bob@example.com")
    staff_client, staff_session = new_resident(make_client, "staff@example.com")
    add_member(
        w["platform"],
        w["platform_session"],
        w["harare"]["id"],
        "staff@example.com",
        CouncilRole.VERIFICATION_OFFICER,
    )
    lat, lon = BULAWAYO
    w["alice_private"] = submit(
        alice, alice_session, report_payload(w, visibility="PRIVATE")
    ).json()["id"]
    w["alice_public_new"] = submit(alice, alice_session, report_payload(w)).json()["id"]
    w["bob_public_verified"] = submit(bob, bob_session, report_payload(w)).json()["id"]
    w["bob_bulawayo_private"] = submit(
        bob,
        bob_session,
        report_payload(
            w, council_id=w["bulawayo"]["id"], visibility="PRIVATE", latitude=lat, longitude=lon
        ),
    ).json()["id"]
    set_status(owner_engine, w["bob_public_verified"], "VERIFIED")
    w["alice"] = alice_session["user"]["id"]
    w["bob"] = bob_session["user"]["id"]
    w["staff"] = staff_session["user"]["id"]
    return w


@pytest.fixture
def app_db() -> Iterator[Session]:
    with get_session_factory()() as session:
        yield session


def visible_ids(db: Session) -> set[str]:
    return set(db.scalars(text("SELECT id::text FROM issues")).all())


def test_anonymous_sees_only_published_public_reports(world, app_db: Session) -> None:
    assert visible_ids(app_db) == {world["bob_public_verified"]}


def test_resident_sees_own_and_published(world, app_db: Session) -> None:
    bind_rls_user(app_db, uuid.UUID(world["alice"]))
    assert visible_ids(app_db) == {
        world["alice_private"],
        world["alice_public_new"],
        world["bob_public_verified"],
    }


def test_council_staff_see_only_their_councils_reports(world, app_db: Session) -> None:
    bind_rls_user(app_db, uuid.UUID(world["staff"]))
    ids = visible_ids(app_db)
    assert world["alice_private"] in ids
    assert world["bob_bulawayo_private"] not in ids


def test_history_follows_report_visibility(world, app_db: Session) -> None:
    bind_rls_user(app_db, uuid.UUID(world["bob"]))
    issue_ids = set(
        app_db.scalars(text("SELECT DISTINCT issue_id::text FROM issue_status_history")).all()
    )
    assert world["alice_private"] not in issue_ids
    assert world["bob_bulawayo_private"] in issue_ids


def test_cannot_file_a_report_as_someone_else(world, app_db: Session) -> None:
    bind_rls_user(app_db, uuid.UUID(world["alice"]))
    with pytest.raises(DBAPIError, match="row-level security"):
        app_db.execute(
            text(
                "INSERT INTO issues (id, council_id, reporter_id, category_id, title, description, "
                "status, visibility, location) VALUES (gen_random_uuid(), :council, :reporter, "
                ":category, 'Forged report', 'Filed in someone else''s name', 'SUBMITTED', "
                "'PUBLIC', 'SRID=4326;POINT(31.05 -17.83)')"
            ),
            {
                "council": world["harare"]["id"],
                "reporter": world["bob"],
                "category": world["categories"]["roads"],
            },
        )


def test_cannot_create_a_pre_verified_report(world, app_db: Session) -> None:
    bind_rls_user(app_db, uuid.UUID(world["alice"]))
    with pytest.raises(DBAPIError, match="row-level security"):
        app_db.execute(
            text(
                "INSERT INTO issues (id, council_id, reporter_id, category_id, title, description, "
                "status, visibility, location) VALUES (gen_random_uuid(), :council, :reporter, "
                ":category, 'Self-published', 'Skipping council review', 'VERIFIED', 'PUBLIC', "
                "'SRID=4326;POINT(31.05 -17.83)')"
            ),
            {
                "council": world["harare"]["id"],
                "reporter": world["alice"],
                "category": world["categories"]["roads"],
            },
        )


def test_reports_and_history_cannot_be_changed_by_the_api_role(world, app_db: Session) -> None:
    bind_rls_user(app_db, uuid.UUID(world["alice"]))
    for statement in (
        "UPDATE issues SET visibility = 'PUBLIC'",
        "DELETE FROM issues",
        "UPDATE issue_status_history SET to_status = 'CLOSED'",
        "DELETE FROM issue_status_history",
    ):
        with pytest.raises(DBAPIError, match="permission denied"):
            app_db.execute(text(statement))
        app_db.rollback()
        bind_rls_user(app_db, uuid.UUID(world["alice"]))
