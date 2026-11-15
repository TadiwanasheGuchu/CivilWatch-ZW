"""In-app notifications and resolution feedback."""

import uuid

import pytest
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError

from app.core.database import bind_rls_user, get_session_factory
from tests.operations_helpers import Actor, assign_to_roads_officer, build_council, move, verify


@pytest.fixture
def c(make_client):
    return build_council(make_client)


def inbox(actor: Actor, query: str = "") -> list[dict]:
    return actor.get(f"/api/v1/notifications?page_size=100{query}").json()["items"]


def unread(actor: Actor) -> int:
    return actor.get("/api/v1/notifications/unread-count").json()["unread"]


def resolve(c) -> None:
    assign_to_roads_officer(c)
    move(c["roads_officer"], c["issue_url"], "IN_PROGRESS")
    move(c["roads_officer"], c["issue_url"], "RESOLVED", note="Patched and compacted.")


# --- Who is told what -------------------------------------------------------------------


def test_reporter_is_told_about_each_change_with_the_councils_message(c) -> None:
    resolve(c)
    titles = [n["title"] for n in reversed(inbox(c["resident"]))]
    ref = c["issue"]["reference"]
    assert titles == [
        f"Your report {ref} is being reviewed",
        f"Your report {ref} has been verified",
        f"Your report {ref} has been assigned to a team",
        f"Work has started on {ref}",
        f"{ref} has been resolved. Was it fixed?",
    ]
    latest = inbox(c["resident"])[0]
    assert latest["body"] == "Patched and compacted."
    assert latest["link"] == f"/reports/{c['issue']['id']}"
    assert unread(c["resident"]) == 5


def test_information_requests_and_answers_reach_the_right_people(c) -> None:
    move(c["verifier"], c["issue_url"], "UNDER_REVIEW")
    move(c["verifier"], c["issue_url"], "NEEDS_INFORMATION", note="Which side of the road?")
    asked = inbox(c["resident"])[0]
    assert asked["kind"] == "information_requested"
    assert asked["body"] == "Which side of the road?"

    c["resident"].post(
        f"/api/v1/issues/{c['issue']['id']}/information", {"note": "Northbound side."}
    )
    answered = inbox(c["verifier"])[0]
    assert answered["kind"] == "information_provided"
    assert answered["body"] == "Northbound side."
    assert answered["link"] == f"/council/{c['council_id']}/reports/{c['issue']['id']}"
    # The reporter is not notified about their own answer.
    assert inbox(c["resident"])[0]["kind"] == "information_requested"


def test_officers_are_told_about_work_assigned_to_them(c) -> None:
    assign_to_roads_officer(c)
    work = inbox(c["roads_officer"])
    assert [n["kind"] for n in work] == ["work_assigned"]
    assert work[0]["title"] == f"New work assigned to you: {c['issue']['reference']}"
    # Reassigning tells the new officer; nobody is told about assigning themselves.
    c["roads_manager"].post(
        f"{c['issue_url']}/assignment",
        {"department_id": c["roads"]["id"], "assignee_user_id": c["roads_manager"].id},
    )
    assert inbox(c["roads_manager"]) == []
    c["roads_manager"].post(
        f"{c['issue_url']}/assignment",
        {"department_id": c["roads"]["id"], "assignee_user_id": c["roads_officer_2"].id},
    )
    assert inbox(c["roads_officer_2"])[0]["kind"] == "work_assigned"


def test_private_report_notifications_stay_with_the_people_involved(c, make_client) -> None:
    verify(c)
    for name in ("water_officer", "water_manager", "admin"):
        assert inbox(c[name]) == [], name


# --- Reading and marking ---------------------------------------------------------------------


def test_marking_notifications_read(c) -> None:
    verify(c)
    items = inbox(c["resident"])
    assert unread(c["resident"]) == 2
    read = c["resident"].post(f"/api/v1/notifications/{items[0]['id']}/read").json()
    assert read["read_at"] is not None
    assert unread(c["resident"]) == 1
    assert len(inbox(c["resident"], "&unread_only=true")) == 1
    assert c["resident"].post("/api/v1/notifications/read-all").json() == {"unread": 0}
    assert unread(c["resident"]) == 0


def test_nobody_can_read_or_mark_someone_elses_notifications(c) -> None:
    verify(c)
    theirs = inbox(c["resident"])[0]["id"]
    assert c["verifier"].post(f"/api/v1/notifications/{theirs}/read").status_code == 404
    assert c["admin"].get("/api/v1/notifications").json()["total"] == 0
    assert unread(c["resident"]) == 2


def test_notifications_need_sign_in_and_csrf(c, client) -> None:
    assert client.get("/api/v1/notifications").status_code == 401
    assert c["resident"].client.post("/api/v1/notifications/read-all").status_code == 403


# --- Was it fixed? ------------------------------------------------------------------------------


def feedback(c, fixed: bool, comment: str | None = None):
    return c["resident"].post(
        f"/api/v1/issues/{c['issue']['id']}/feedback", {"fixed": fixed, "comment": comment}
    )


def test_feedback_only_after_resolution_and_only_once(c) -> None:
    assert feedback(c, True).status_code == 409
    resolve(c)
    given = feedback(c, True, "Smooth now, thank you.")
    assert given.status_code == 201
    assert given.json()["fixed"] is True
    assert feedback(c, False).status_code == 409
    own = c["resident"].get(f"/api/v1/issues/{c['issue']['id']}").json()
    assert own["feedback"]["comment"] == "Smooth now, thank you."
    staff = c["verifier"].get(c["issue_url"]).json()
    assert staff["feedback"]["fixed"] is True


def test_not_fixed_feedback_alerts_the_officer_who_resolved_it(c) -> None:
    resolve(c)
    feedback(c, False, "The hole is back after one day of rain.")
    alert = inbox(c["roads_officer"])[0]
    assert alert["kind"] == "feedback_not_fixed"
    assert alert["body"] == "The hole is back after one day of rain."
    # Nothing reopens automatically; the council decides.
    assert c["admin"].get(c["issue_url"]).json()["status"] == "RESOLVED"


def test_only_the_reporter_gives_feedback_and_it_is_never_public(
    c, make_client, owner_engine
) -> None:
    resolve(c)
    other = c["verifier"].post(f"/api/v1/issues/{c['issue']['id']}/feedback", {"fixed": True})
    assert other.status_code == 404
    feedback(c, False, "Private comment about my street.")
    with owner_engine.begin() as connection:
        connection.execute(
            text("UPDATE issues SET visibility = 'PUBLIC' WHERE id = :i"), {"i": c["issue"]["id"]}
        )
    public = make_client().get(f"/api/v1/issues/{c['issue']['id']}")
    assert public.status_code == 200
    assert "Private comment" not in public.text and "feedback" not in public.json()


def test_feedback_comment_is_validated(c) -> None:
    resolve(c)
    assert feedback(c, True, "x" * 1001).status_code == 422
    assert (
        c["resident"]
        .post(f"/api/v1/issues/{c['issue']['id']}/feedback", {"comment": "?"})
        .status_code
        == 422
    )


# --- Database rules -------------------------------------------------------------------------------


def test_rls_keeps_notifications_private_and_tied_to_visible_reports(c, make_client) -> None:
    from tests.issue_helpers import new_resident

    verify(c)
    _, stranger = new_resident(make_client, "stranger@example.com")
    with get_session_factory()() as db:
        bind_rls_user(db, uuid.UUID(stranger["user"]["id"]))
        assert db.scalar(text("SELECT count(*) FROM notifications")) == 0
        with pytest.raises(DBAPIError, match="row-level security"):
            db.execute(
                text(
                    "INSERT INTO notifications (id, user_id, issue_id, kind, title, link, "
                    "created_at) VALUES (gen_random_uuid(), :u, :i, 'status_changed', 'Spoof', "
                    "'/x', now())"
                ),
                {"u": c["resident"].id, "i": c["issue"]["id"]},
            )


def test_rls_feedback_only_from_the_reporter_after_resolution(c) -> None:
    with get_session_factory()() as db:
        bind_rls_user(db, uuid.UUID(c["resident"].id))
        with pytest.raises(DBAPIError, match="row-level security"):
            db.execute(
                text(
                    "INSERT INTO resolution_feedback (id, issue_id, council_id, reporter_id, "
                    "fixed, created_at) VALUES (gen_random_uuid(), :i, :c, :r, true, now())"
                ),
                {"i": c["issue"]["id"], "c": c["council_id"], "r": c["resident"].id},
            )
