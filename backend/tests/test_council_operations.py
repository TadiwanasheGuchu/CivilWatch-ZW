"""Council queue, departments, staff notes, and isolation of council operations."""

import uuid

import pytest
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError

from app.core.database import bind_rls_user, get_session_factory
from app.models.councils import CouncilRole
from tests.conftest import add_member, register, sign_in
from tests.issue_helpers import BULAWAYO, report_payload, set_status, submit
from tests.operations_helpers import Actor, assign_to_roads_officer, build_council, move


@pytest.fixture
def c(make_client):
    return build_council(make_client)


# --- Queue ---


def test_queue_lists_the_councils_reports_including_private_ones(c) -> None:
    body = c["verifier"].get(f"{c['base']}/issues").json()
    assert body["total"] == 1
    item = body["items"][0]
    assert item["visibility"] == "PRIVATE"
    assert item["assignment"] is None


def test_queue_filters_search_and_sort(c, owner_engine) -> None:
    resident = c["resident"]
    second = submit(
        resident.client, resident.session, report_payload(c, title="Streetlight 50% dark_area")
    ).json()
    assign_to_roads_officer(c)
    base = c["base"]

    def ids(query: str) -> list[str]:
        return [i["id"] for i in c["roads_officer"].get(f"{base}/issues?{query}").json()["items"]]

    assert ids("status=ASSIGNED") == [c["issue"]["id"]]
    assert set(ids("status=ASSIGNED&status=SUBMITTED")) == {c["issue"]["id"], second["id"]}
    assert ids("assigned_to_me=true") == [c["issue"]["id"]]
    assert ids(f"department_id={c['roads']['id']}") == [c["issue"]["id"]]
    assert ids(f"department_id={c['water']['id']}") == []
    assert ids(f"q={second['reference']}") == [second["id"]]
    assert ids(f"q={second['reference'][3:].lstrip('0')}") == [second["id"]]
    assert ids("q=50%25") == [second["id"]]  # "%" is matched literally
    assert ids("q=_") == [second["id"]]
    assert ids("sort=oldest")[0] == c["issue"]["id"]
    assert ids("sort=newest")[0] == second["id"]
    assert c["admin"].get(f"{base}/issues?status=FIXED").status_code == 422

    listed = c["admin"].get(f"{base}/issues?status=ASSIGNED").json()["items"][0]
    assert listed["assignment"]["department"]["name"] == "Roads"
    assert listed["assignment"]["assignee"]["full_name"] == "Roads Officer"


def test_queue_summary_counts_real_data(c) -> None:
    assign_to_roads_officer(c)
    summary = c["roads_officer"].get(f"{c['base']}/issues/summary").json()
    counts = {row["status"]: row["count"] for row in summary["counts"]}
    assert counts["ASSIGNED"] == 1
    assert sum(counts.values()) == 1
    assert summary["assigned_to_me"] == 1
    assert c["verifier"].get(f"{c['base']}/issues/summary").json()["assigned_to_me"] == 0


def test_staff_see_the_reporters_name_but_not_their_email(c) -> None:
    detail = c["verifier"].get(c["issue_url"])
    assert detail.json()["reporter_name"] == "Tendai Moyo"
    assert "resident@example.com" not in detail.text
    assert "resident@example.com" not in c["verifier"].get(f"{c['base']}/issues").text


# --- Who may see council operations ---


def test_residents_and_platform_admins_cannot_use_council_operations(c) -> None:
    for client in (c["resident"].client, c["platform"]):
        for path in ("/issues", "/issues/summary", f"/issues/{c['issue']['id']}", "/departments"):
            assert client.get(f"{c['base']}{path}").status_code == 403, path


def test_another_councils_staff_cannot_see_or_act_on_these_reports(c, make_client) -> None:
    client = make_client()
    register(client, email="admin@bulawayo.example.com")
    add_member(
        c["platform"],
        c["platform_session"],
        c["bulawayo"]["id"],
        "admin@bulawayo.example.com",
        CouncilRole.COUNCIL_ADMIN,
    )
    outsider = Actor(client, sign_in(client, "admin@bulawayo.example.com"))
    # Through their own council's URL: the report is simply not there.
    own_base = f"/api/v1/councils/{c['bulawayo']['id']}"
    assert outsider.get(f"{own_base}/issues").json()["total"] == 0
    assert outsider.get(f"{own_base}/issues/{c['issue']['id']}").status_code == 404
    assert (
        move(outsider, f"{own_base}/issues/{c['issue']['id']}", "UNDER_REVIEW").status_code == 404
    )
    assigned = outsider.post(
        f"{own_base}/issues/{c['issue']['id']}/assignment", {"department_id": c["roads"]["id"]}
    )
    assert assigned.status_code in (404, 422)
    # Through Harare's URL: not a member.
    assert outsider.get(c["issue_url"]).status_code == 403
    assert c["admin"].get(c["issue_url"]).json()["status"] == "SUBMITTED"


# --- Staff-only notes ---


def test_internal_notes_never_reach_residents_or_the_public(c, owner_engine, make_client) -> None:
    secret = "Contractor quoted 4000 USD; budget review pending."
    response = c["roads_officer"].post(f"{c['issue_url']}/updates", {"body": secret})
    assert response.status_code == 201
    assert response.json()["updates"][0]["author"] == "Roads Officer"

    # Make it public and verified, so everyone can read the report itself.
    with owner_engine.begin() as connection:
        connection.execute(
            text("UPDATE issues SET visibility = 'PUBLIC' WHERE id = :i"), {"i": c["issue"]["id"]}
        )
    set_status(owner_engine, c["issue"]["id"], "VERIFIED")
    for client in (c["resident"].client, make_client()):
        for path in (f"/api/v1/issues/{c['issue']['id']}", "/api/v1/issues", "/api/v1/issues/mine"):
            body = client.get(path).text
            assert "budget review" not in body, path


def test_notes_need_text(c) -> None:
    assert c["verifier"].post(f"{c['issue_url']}/updates", {"body": "   "}).status_code == 422


def test_public_timeline_shows_statuses_without_messages(c, owner_engine, make_client) -> None:
    with owner_engine.begin() as connection:
        connection.execute(
            text("UPDATE issues SET visibility = 'PUBLIC' WHERE id = :i"), {"i": c["issue"]["id"]}
        )
    move(c["verifier"], c["issue_url"], "UNDER_REVIEW")
    move(c["verifier"], c["issue_url"], "NEEDS_INFORMATION", note="Is the pothole near your house?")
    c["resident"].post(
        f"/api/v1/issues/{c['issue']['id']}/information", {"note": "Yes, at number 12."}
    )
    move(c["verifier"], c["issue_url"], "VERIFIED")
    public = make_client().get(f"/api/v1/issues/{c['issue']['id']}")
    assert public.status_code == 200
    assert "number 12" not in public.text and "your house" not in public.text
    assert all("note" not in h for h in public.json()["history"])


# --- Departments ---


def test_departments_are_managed_by_council_administrators(c) -> None:
    base = c["base"]
    names = [d["name"] for d in c["roads_officer"].get(f"{base}/departments").json()]
    assert names == ["Roads", "Water and Sewerage"]
    assert c["roads_manager"].post(f"{base}/departments", {"name": "Parks"}).status_code == 403
    assert c["admin"].post(f"{base}/departments", {"name": "roads"}).status_code == 409
    assert c["admin"].post(f"{base}/departments", {"name": "X"}).status_code == 422
    renamed = c["admin"].patch(f"{base}/departments/{c['water']['id']}", {"name": "Water"})
    assert renamed.json()["name"] == "Water"
    audit = [
        e["action"] for e in c["admin"].get(f"{base}/audit-logs?page_size=100").json()["items"]
    ]
    assert "department.created" in audit and "department.updated" in audit


def test_staff_departments_follow_their_role(c) -> None:
    base = c["base"]
    members = {
        m["user_id"]: m for m in c["admin"].get(f"{base}/members?page_size=100").json()["items"]
    }
    officer = members[c["roads_officer"].id]
    assert officer["department"]["name"] == "Roads"
    verifier = members[c["verifier"].id]
    bad = c["admin"].patch(
        f"{base}/members/{verifier['membership_id']}", {"department_id": c["roads"]["id"]}
    )
    assert bad.status_code == 422
    foreign = c["admin"].patch(
        f"{base}/members/{officer['membership_id']}", {"department_id": str(uuid.uuid4())}
    )
    assert foreign.status_code == 422
    moved = (
        c["admin"]
        .patch(f"{base}/members/{officer['membership_id']}", {"role": "verification_officer"})
        .json()
    )
    assert moved["role"] == "verification_officer"
    assert moved["department"] is None
    assert c["admin"].patch(f"{base}/members/{officer['membership_id']}", {}).status_code == 422


# --- Database rules (as the API role) ---


def _as(user_id: str):
    db = get_session_factory()()
    bind_rls_user(db, uuid.UUID(user_id))
    return db


def test_rls_keeps_staff_notes_and_assignments_inside_the_council(c) -> None:
    c["roads_officer"].post(f"{c['issue_url']}/updates", {"body": "Internal"})
    assign_to_roads_officer(c)
    with _as(c["resident"].id) as db:
        assert db.scalar(text("SELECT count(*) FROM issue_updates")) == 0
        assert db.scalar(text("SELECT count(*) FROM issue_assignments")) == 0
        assert db.scalar(text("SELECT count(*) FROM departments")) == 0
    with get_session_factory()() as anonymous:
        assert anonymous.scalar(text("SELECT count(*) FROM issue_updates")) == 0


def test_rls_limits_who_can_change_a_report(c) -> None:
    issue_id = c["issue"]["id"]
    with _as(c["resident"].id) as db:
        # Reporters cannot change status, except to answer a request for information.
        assert (
            db.execute(
                text("UPDATE issues SET status = 'VERIFIED' WHERE id = :i"), {"i": issue_id}
            ).rowcount
            == 0
        )
    with _as(c["verifier"].id) as db:
        updated = db.execute(
            text("UPDATE issues SET status = 'UNDER_REVIEW' WHERE id = :i"), {"i": issue_id}
        )
        assert updated.rowcount == 1
        db.rollback()


def test_rls_reporter_can_only_move_from_needs_information_to_review(c) -> None:
    move(c["verifier"], c["issue_url"], "UNDER_REVIEW")
    move(c["verifier"], c["issue_url"], "NEEDS_INFORMATION", note="Which side?")
    issue_id = c["issue"]["id"]
    with _as(c["resident"].id) as db:
        with pytest.raises(DBAPIError, match="row-level security"):
            db.execute(text("UPDATE issues SET status = 'VERIFIED' WHERE id = :i"), {"i": issue_id})
        db.rollback()
    with _as(c["resident"].id) as db:
        assert (
            db.execute(
                text("UPDATE issues SET status = 'UNDER_REVIEW' WHERE id = :i"), {"i": issue_id}
            ).rowcount
            == 1
        )
        db.rollback()


def test_rls_other_council_staff_cannot_change_reports(c, make_client) -> None:
    lat, lon = BULAWAYO
    resident = c["resident"]
    elsewhere = submit(
        resident.client,
        resident.session,
        report_payload(c, council_id=c["bulawayo"]["id"], latitude=lat, longitude=lon),
    ).json()
    with _as(c["admin"].id) as db:
        assert (
            db.execute(
                text("UPDATE issues SET status = 'UNDER_REVIEW' WHERE id = :i"),
                {"i": elsewhere["id"]},
            ).rowcount
            == 0
        )


def test_rls_only_admins_create_departments(c) -> None:
    with _as(c["roads_manager"].id) as db, pytest.raises(DBAPIError, match="row-level security"):
        db.execute(
            text(
                "INSERT INTO departments (id, council_id, name, created_at, updated_at) "
                "VALUES (gen_random_uuid(), :c, 'Shadow', now(), now())"
            ),
            {"c": c["council_id"]},
        )


def test_rls_staff_notes_are_append_only(c) -> None:
    c["roads_officer"].post(f"{c['issue_url']}/updates", {"body": "Original"})
    with _as(c["admin"].id) as db:
        for statement in ("UPDATE issue_updates SET body = 'Edited'", "DELETE FROM issue_updates"):
            with pytest.raises(DBAPIError, match="permission denied"):
                db.execute(text(statement))
            db.rollback()
            bind_rls_user(db, uuid.UUID(c["admin"].id))
