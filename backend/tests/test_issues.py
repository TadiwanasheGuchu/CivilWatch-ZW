"""Report submission, the resident's own reports, and public browsing."""

import re
from collections.abc import Callable

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import Engine, text

from app.core.config import get_settings
from tests.conftest import csrf_headers
from tests.issue_helpers import (
    BULAWAYO,
    new_resident,
    report_payload,
    set_status,
    setup_councils,
    submit,
)


@pytest.fixture
def world(make_client: Callable[[], TestClient]):
    return setup_councils(make_client)


# --- Categories ------------------------------------------------------------------


def test_categories_are_public_and_ordered(client: TestClient) -> None:
    response = client.get("/api/v1/categories")
    assert response.status_code == 200
    codes = [c["code"] for c in response.json()]
    assert codes == [
        "roads",
        "streetlights",
        "drainage",
        "water",
        "waste",
        "public-buildings",
        "bridges-pavements",
        "other",
    ]


# --- Submission --------------------------------------------------------------------


def test_submission_requires_sign_in_and_csrf(world, client: TestClient) -> None:
    assert client.post("/api/v1/issues", json=report_payload(world)).status_code == 401
    _, _ = new_resident(lambda: client, "r@example.com")
    assert client.post("/api/v1/issues", json=report_payload(world)).status_code == 403


def test_submit_report(world, make_client) -> None:
    client, session = new_resident(make_client, "chipo@example.com")
    response = submit(client, session, report_payload(world, visibility="PRIVATE"))
    assert response.status_code == 201, response.text
    body = response.json()
    assert re.fullmatch(r"CW-\d{6}", body["reference"])
    assert body["status"] == "SUBMITTED"
    assert body["visibility"] == "PRIVATE"
    assert body["is_published"] is False
    assert body["council"]["slug"] == "harare"
    assert body["category"]["code"] == "roads"
    assert body["latitude"] == pytest.approx(-17.8292)
    assert body["longitude"] == pytest.approx(31.0522)
    assert "reporter_id" not in body

    detail = client.get(f"/api/v1/issues/{body['id']}").json()
    assert detail["history"] == [
        {
            "from_status": None,
            "to_status": "SUBMITTED",
            "note": None,
            "created_at": detail["history"][0]["created_at"],
        }
    ]


def test_reference_numbers_increase(world, make_client) -> None:
    client, session = new_resident(make_client, "seq@example.com")
    first = submit(client, session, report_payload(world)).json()["reference"]
    second = submit(client, session, report_payload(world)).json()["reference"]
    assert int(second[3:]) == int(first[3:]) + 1


@pytest.mark.parametrize(
    ("override", "field"),
    [
        ({"title": "Hole"}, "title"),
        ({"description": "Too short"}, "description"),
        ({"title": "Bad\x00title here"}, "title"),
        ({"latitude": 95}, "latitude"),
        ({"visibility": "FRIENDS"}, "visibility"),
        ({"status": "VERIFIED"}, "status"),
        ({"reporter_id": "00000000-0000-0000-0000-000000000000"}, "reporter_id"),
    ],
)
def test_invalid_reports_are_rejected(world, make_client, override, field) -> None:
    client, session = new_resident(make_client, "v@example.com")
    response = submit(client, session, report_payload(world, **override))
    assert response.status_code == 422
    locations = [d["location"] for d in response.json()["error"]["details"]]
    assert ["body", field] in locations


def test_unknown_council_and_category_are_field_errors(world, make_client) -> None:
    client, session = new_resident(make_client, "u@example.com")
    missing = "00000000-0000-0000-0000-000000000000"
    for field in ("council_id", "category_id"):
        response = submit(client, session, report_payload(world, **{field: missing}))
        assert response.status_code == 422
        assert response.json()["error"]["details"][0]["location"] == ["body", field]


def test_inactive_council_cannot_receive_reports(world, make_client, owner_engine: Engine) -> None:
    with owner_engine.begin() as connection:
        connection.execute(text("UPDATE councils SET is_active = false WHERE slug = 'harare'"))
    client, session = new_resident(make_client, "i@example.com")
    response = submit(client, session, report_payload(world))
    assert response.status_code == 422


def test_location_outside_service_area_is_rejected(world, make_client) -> None:
    client, session = new_resident(make_client, "far@example.com")
    response = submit(client, session, report_payload(world, latitude=51.5, longitude=-0.12))
    assert response.status_code == 422
    detail = response.json()["error"]["details"][0]
    assert detail["location"] == ["body", "latitude"]
    assert "outside the area" in detail["message"]


def test_council_boundary_is_enforced_when_known(world, make_client, owner_engine: Engine) -> None:
    # A box around central Harare.
    with owner_engine.begin() as connection:
        connection.execute(
            text(
                "UPDATE councils SET boundary = "
                "ST_Multi(ST_MakeEnvelope(30.9, -17.95, 31.2, -17.7, 4326)) "
                "WHERE slug = 'harare'"
            )
        )
    client, session = new_resident(make_client, "b@example.com")
    lat, lon = BULAWAYO
    outside = submit(client, session, report_payload(world, latitude=lat, longitude=lon))
    assert outside.status_code == 422
    assert "Harare City Council" in outside.json()["error"]["details"][0]["message"]
    assert submit(client, session, report_payload(world)).status_code == 201


def test_reports_are_rate_limited_per_user(world, make_client) -> None:
    client, session = new_resident(make_client, "busy@example.com")
    for _ in range(get_settings().reports_per_user):
        assert submit(client, session, report_payload(world)).status_code == 201
    limited = submit(client, session, report_payload(world))
    assert limited.status_code == 429
    assert int(limited.headers["Retry-After"]) > 0


# --- Own reports ---------------------------------------------------------------------


def test_my_reports_lists_only_own_including_private(world, make_client) -> None:
    alice, alice_session = new_resident(make_client, "alice@example.com")
    bob, bob_session = new_resident(make_client, "bob@example.com")
    submit(alice, alice_session, report_payload(world, title="Alice public report"))
    submit(
        alice,
        alice_session,
        report_payload(world, title="Alice private report", visibility="PRIVATE"),
    )
    submit(bob, bob_session, report_payload(world, title="Bob report"))

    body = alice.get("/api/v1/issues/mine").json()
    assert body["total"] == 2
    assert [i["title"] for i in body["items"]] == ["Alice private report", "Alice public report"]
    assert alice.get("/api/v1/issues/mine?page_size=1&page=2").json()["items"][0]["title"] == (
        "Alice public report"
    )


def test_my_reports_requires_sign_in(client: TestClient) -> None:
    assert client.get("/api/v1/issues/mine").status_code == 401


# --- Public browsing and visibility ------------------------------------------------------


def test_only_verified_public_reports_are_published(world, make_client, owner_engine) -> None:
    reporter, session = new_resident(make_client, "rep@example.com")
    ids = {}
    for name, visibility in (
        ("public-unverified", "PUBLIC"),
        ("public-verified", "PUBLIC"),
        ("private-verified", "PRIVATE"),
        ("public-rejected", "PUBLIC"),
        ("public-duplicate", "PUBLIC"),
    ):
        ids[name] = submit(
            reporter, session, report_payload(world, title=f"Report {name}", visibility=visibility)
        ).json()["id"]
    set_status(owner_engine, ids["public-verified"], "VERIFIED")
    set_status(owner_engine, ids["private-verified"], "VERIFIED")
    set_status(owner_engine, ids["public-rejected"], "REJECTED")
    set_status(owner_engine, ids["public-duplicate"], "DUPLICATE")

    anonymous = make_client()
    listing = anonymous.get("/api/v1/issues").json()
    assert [i["id"] for i in listing["items"]] == [ids["public-verified"]]
    assert listing["total"] == 1

    for name, issue_id in ids.items():
        expected = 200 if name == "public-verified" else 404
        assert anonymous.get(f"/api/v1/issues/{issue_id}").status_code == expected, name
    # The reporter still sees every one of their own reports.
    for issue_id in ids.values():
        assert reporter.get(f"/api/v1/issues/{issue_id}").status_code == 200


def test_public_view_never_identifies_the_reporter(world, make_client, owner_engine) -> None:
    reporter, session = new_resident(make_client, "named.person@example.com")
    issue_id = submit(reporter, session, report_payload(world)).json()["id"]
    set_status(owner_engine, issue_id, "VERIFIED")
    anonymous = make_client()
    for response in (anonymous.get(f"/api/v1/issues/{issue_id}"), anonymous.get("/api/v1/issues")):
        assert "named.person" not in response.text
        assert "reporter" not in response.text
        assert "visibility" not in response.text


def test_another_residents_private_report_is_not_found(world, make_client, owner_engine) -> None:
    owner, owner_session = new_resident(make_client, "owner@example.com")
    issue_id = submit(owner, owner_session, report_payload(world, visibility="PRIVATE")).json()[
        "id"
    ]
    set_status(owner_engine, issue_id, "VERIFIED")
    other, _ = new_resident(make_client, "other@example.com")
    response = other.get(f"/api/v1/issues/{issue_id}")
    assert response.status_code == 404
    assert "Samora" not in response.text


@pytest.mark.parametrize("method", ["put", "patch", "delete"])
def test_reports_cannot_be_modified_through_the_api(world, make_client, method) -> None:
    owner, owner_session = new_resident(make_client, "owner@example.com")
    issue_id = submit(owner, owner_session, report_payload(world, visibility="PRIVATE")).json()[
        "id"
    ]
    other, other_session = new_resident(make_client, "other@example.com")
    for client, session in ((other, other_session), (owner, owner_session)):
        response = client.request(
            method.upper(),
            f"/api/v1/issues/{issue_id}",
            json={"visibility": "PUBLIC", "status": "CLOSED"},
            headers=csrf_headers(session),
        )
        assert response.status_code == 405
    detail = owner.get(f"/api/v1/issues/{issue_id}").json()
    assert (detail["visibility"], detail["status"]) == ("PRIVATE", "SUBMITTED")


def test_public_browsing_filters(world, make_client, owner_engine) -> None:
    reporter, session = new_resident(make_client, "f@example.com")
    lat, lon = BULAWAYO
    specs = [
        ("harare", "roads", "VERIFIED", {}),
        ("harare", "water", "RESOLVED", {}),
        ("bulawayo", "roads", "IN_PROGRESS", {"latitude": lat, "longitude": lon}),
    ]
    for council, category, status, extra in specs:
        issue = submit(
            reporter,
            session,
            report_payload(
                world,
                council_id=world[council]["id"],
                category_id=world["categories"][category],
                **extra,
            ),
        ).json()
        set_status(owner_engine, issue["id"], status)

    def count(query: str) -> int:
        return reporter.get(f"/api/v1/issues?{query}").json()["total"]

    assert count("") == 3
    assert count(f"council_id={world['harare']['id']}") == 2
    assert count("category=roads") == 2
    assert count("status=RESOLVED") == 1
    assert reporter.get("/api/v1/issues?status=SUBMITTED").status_code == 422
    assert reporter.get("/api/v1/issues?category=DROP%20TABLE").status_code == 422
