"""Report workflow: permitted and refused status changes, assignment, notes."""

import threading

import pytest

from tests.operations_helpers import assign_to_roads_officer, build_council, move, verify


@pytest.fixture
def c(make_client):
    return build_council(make_client)


def statuses(detail: dict) -> list[str]:
    return [h["to_status"] for h in detail["history"]]


# --- The full journey ---


def test_full_lifecycle_with_each_role_doing_its_part(c) -> None:
    url = c["issue_url"]
    assert move(c["verifier"], url, "UNDER_REVIEW").status_code == 200
    assert move(c["verifier"], url, "VERIFIED").status_code == 200
    assigned = (
        c["roads_manager"]
        .post(
            f"{url}/assignment",
            {"department_id": c["roads"]["id"], "assignee_user_id": c["roads_officer"].id},
        )
        .json()
    )
    assert assigned["status"] == "ASSIGNED"
    assert assigned["assignment"]["department"]["name"] == "Roads"
    assert assigned["assignment"]["assignee"]["id"] == c["roads_officer"].id
    assert move(c["roads_officer"], url, "IN_PROGRESS").status_code == 200
    resolved = move(c["roads_officer"], url, "RESOLVED", note="Pothole filled and compacted.")
    assert resolved.status_code == 200
    closed = move(c["roads_manager"], url, "CLOSED").json()
    assert closed["status"] == "CLOSED"
    assert statuses(closed) == [
        "SUBMITTED",
        "UNDER_REVIEW",
        "VERIFIED",
        "ASSIGNED",
        "IN_PROGRESS",
        "RESOLVED",
        "CLOSED",
    ]
    assert closed["history"][3]["note"] == "Assigned to the Roads department."
    assert closed["history"][1]["changed_by"] == "Verifier"
    assert closed["available_transitions"] == []

    # The reporter follows along, including the council's messages to them.
    own = c["resident"].get(f"/api/v1/issues/{c['issue']['id']}").json()
    assert statuses(own) == statuses(closed)
    assert own["history"][5]["note"] == "Pothole filled and compacted."
    assert "changed_by" not in own["history"][0]


def test_staff_see_only_the_changes_they_may_make(c) -> None:
    url = c["issue_url"]
    labels = {
        name: [t["to_status"] for t in c[name].get(url).json()["available_transitions"]]
        for name in ("verifier", "roads_manager", "roads_officer", "admin")
    }
    assert labels["verifier"] == ["UNDER_REVIEW", "REJECTED", "DUPLICATE"]
    assert labels["roads_manager"] == []
    assert labels["roads_officer"] == []
    assert labels["admin"] == ["UNDER_REVIEW", "REJECTED", "DUPLICATE"]
    assert c["verifier"].get(url).json()["can_assign"] is False


# --- Mandatory: invalid status transitions are rejected ---


@pytest.mark.parametrize(
    "to_status", ["VERIFIED", "IN_PROGRESS", "RESOLVED", "CLOSED", "ASSIGNED", "SUBMITTED"]
)
def test_invalid_transitions_from_submitted_are_rejected(c, to_status) -> None:
    response = move(c["admin"], c["issue_url"], to_status)
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "invalid_transition"
    assert c["admin"].get(c["issue_url"]).json()["status"] == "SUBMITTED"


def test_terminal_reports_cannot_move(c) -> None:
    assert (
        move(
            c["verifier"], c["issue_url"], "REJECTED", note="Outside council property."
        ).status_code
        == 200
    )
    for to_status in ("UNDER_REVIEW", "VERIFIED", "SUBMITTED", "CLOSED"):
        assert move(c["admin"], c["issue_url"], to_status).status_code == 409


def test_unknown_status_is_a_validation_error(c) -> None:
    assert move(c["admin"], c["issue_url"], "FIXED").status_code == 422


def test_notes_are_required_where_the_reporter_needs_an_explanation(c) -> None:
    for to_status in ("REJECTED",):
        response = move(c["verifier"], c["issue_url"], to_status)
        assert response.status_code == 422
        assert response.json()["error"]["details"][0]["location"] == ["body", "note"]
    move(c["verifier"], c["issue_url"], "UNDER_REVIEW")
    assert move(c["verifier"], c["issue_url"], "NEEDS_INFORMATION", note="   ").status_code == 422


def test_concurrent_changes_cannot_both_succeed(c) -> None:
    move(c["verifier"], c["issue_url"], "UNDER_REVIEW")
    results: list[int] = []

    def act(actor, to_status, note=None):
        results.append(move(actor, c["issue_url"], to_status, note=note).status_code)

    threads = [
        threading.Thread(target=act, args=(c["verifier"], "VERIFIED")),
        threading.Thread(target=act, args=(c["admin"], "REJECTED", "Not council property.")),
    ]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert sorted(results) == [200, 409]
    detail = c["admin"].get(c["issue_url"]).json()
    assert statuses(detail).count("VERIFIED") + statuses(detail).count("REJECTED") == 1


# --- Mandatory: unauthorised staff cannot assign ---


def test_roles_without_assign_permission_cannot_assign(c) -> None:
    verify(c)
    body = {"department_id": c["roads"]["id"]}
    for name in ("verifier", "roads_officer", "water_officer"):
        response = c[name].post(f"{c['issue_url']}/assignment", body)
        assert response.status_code == 403, name
    assert c["admin"].get(c["issue_url"]).json()["status"] == "VERIFIED"


def test_managers_assign_only_within_their_department(c) -> None:
    verify(c)
    response = c["water_manager"].post(
        f"{c['issue_url']}/assignment", {"department_id": c["roads"]["id"]}
    )
    assert response.status_code == 403
    # Once Roads holds it, the Water manager cannot take it over either.
    c["roads_manager"].post(f"{c['issue_url']}/assignment", {"department_id": c["roads"]["id"]})
    stolen = c["water_manager"].post(
        f"{c['issue_url']}/assignment", {"department_id": c["water"]["id"]}
    )
    assert stolen.status_code == 403
    assert c["water_manager"].get(c["issue_url"]).json()["can_assign"] is False


def test_assignee_must_work_in_the_chosen_department(c) -> None:
    verify(c)
    for assignee in (c["water_officer"].id, c["verifier"].id, c["resident"].id):
        response = c["admin"].post(
            f"{c['issue_url']}/assignment",
            {"department_id": c["roads"]["id"], "assignee_user_id": assignee},
        )
        assert response.status_code == 422
        assert response.json()["error"]["details"][0]["location"] == ["body", "assignee_user_id"]


def test_reports_must_be_verified_before_assignment(c) -> None:
    response = c["admin"].post(f"{c['issue_url']}/assignment", {"department_id": c["roads"]["id"]})
    assert response.status_code == 409


def test_reassignment_keeps_status_and_history(c) -> None:
    assign_to_roads_officer(c)
    response = (
        c["roads_manager"]
        .post(
            f"{c['issue_url']}/assignment",
            {"department_id": c["roads"]["id"], "assignee_user_id": c["roads_officer_2"].id},
        )
        .json()
    )
    assert response["status"] == "ASSIGNED"
    assert response["assignment"]["assignee"]["id"] == c["roads_officer_2"].id
    assert statuses(response).count("ASSIGNED") == 1


def test_inactive_departments_cannot_receive_work(c) -> None:
    verify(c)
    c["admin"].patch(f"{c['base']}/departments/{c['water']['id']}", {"is_active": False})
    response = c["admin"].post(f"{c['issue_url']}/assignment", {"department_id": c["water"]["id"]})
    assert response.status_code == 422


# --- Work is limited to the people it was given to ---


def test_only_the_assignee_or_their_manager_can_work_on_it(c) -> None:
    assign_to_roads_officer(c)
    for name in ("roads_officer_2", "water_officer", "water_manager", "verifier"):
        assert move(c[name], c["issue_url"], "IN_PROGRESS").status_code == 403, name
    assert move(c["roads_manager"], c["issue_url"], "IN_PROGRESS").status_code == 200
    assert move(c["roads_officer"], c["issue_url"], "RESOLVED").status_code == 422  # note required
    assert move(c["roads_officer"], c["issue_url"], "RESOLVED", note="Patched.").status_code == 200
    # Closing is for managers and administrators, not officers.
    assert move(c["roads_officer"], c["issue_url"], "CLOSED").status_code == 403
    reopened = move(
        c["roads_manager"], c["issue_url"], "IN_PROGRESS", note="Patch already cracked."
    )
    assert reopened.status_code == 200


def test_maintenance_officers_cannot_review(c) -> None:
    assert move(c["roads_officer"], c["issue_url"], "UNDER_REVIEW").status_code == 403


# --- Duplicates ---


def test_duplicate_needs_a_valid_original_in_the_same_council(c, make_client) -> None:
    from tests.issue_helpers import BULAWAYO, report_payload, submit

    resident = c["resident"]
    original = submit(resident.client, resident.session, report_payload(c)).json()
    lat, lon = BULAWAYO
    elsewhere = submit(
        resident.client,
        resident.session,
        report_payload(c, council_id=c["bulawayo"]["id"], latitude=lat, longitude=lon),
    ).json()

    assert move(c["verifier"], c["issue_url"], "DUPLICATE").status_code == 422
    for reference in (elsewhere["reference"], c["issue"]["reference"], "CW-999999"):
        response = move(
            c["verifier"], c["issue_url"], "DUPLICATE", duplicate_of_reference=reference
        )
        assert response.status_code == 422, reference
    ok = move(
        c["verifier"], c["issue_url"], "DUPLICATE", duplicate_of_reference=original["reference"]
    )
    assert ok.status_code == 200
    assert ok.json()["duplicate_of"]["reference"] == original["reference"]


# --- Asking the reporter for information ---


def test_reporter_answers_a_request_for_information(c) -> None:
    from tests.photo_helpers import jpeg_with_gps

    url, resident = c["issue_url"], c["resident"]
    issue_id = c["issue"]["id"]
    move(c["verifier"], url, "UNDER_REVIEW")
    asked = move(c["verifier"], url, "NEEDS_INFORMATION", note="Which side of the road is it on?")
    assert asked.status_code == 200

    own = resident.get(f"/api/v1/issues/{issue_id}").json()
    assert own["status"] == "NEEDS_INFORMATION"
    assert own["history"][-1]["note"] == "Which side of the road is it on?"

    # Photos can be added while the council waits.
    photo = resident.client.post(
        f"/api/v1/issues/{issue_id}/photos",
        files={"file": ("p.jpg", jpeg_with_gps(), "image/jpeg")},
        headers={"X-CSRF-Token": resident.session["csrf_token"]},
    )
    assert photo.status_code == 201

    answered = resident.post(
        f"/api/v1/issues/{issue_id}/information", {"note": "The northbound side."}
    )
    assert answered.status_code == 200
    assert answered.json()["status"] == "UNDER_REVIEW"
    staff_view = c["verifier"].get(url).json()
    assert staff_view["history"][-1]["note"] == "The northbound side."
    assert staff_view["history"][-1]["changed_by"] == "Tendai Moyo"  # the reporter

    again = resident.post(f"/api/v1/issues/{issue_id}/information", {"note": "More."})
    assert again.status_code == 409


def test_only_the_reporter_can_answer(c, make_client) -> None:
    from tests.issue_helpers import new_resident

    move(c["verifier"], c["issue_url"], "UNDER_REVIEW")
    move(c["verifier"], c["issue_url"], "NEEDS_INFORMATION", note="Where exactly?")
    other_client, other_session = new_resident(make_client, "other@example.com")
    response = other_client.post(
        f"/api/v1/issues/{c['issue']['id']}/information",
        json={"note": "Hijack"},
        headers={"X-CSRF-Token": other_session["csrf_token"]},
    )
    assert response.status_code == 404
