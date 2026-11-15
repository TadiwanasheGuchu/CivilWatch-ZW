"""Council performance figures, public statistics and CSV exports."""

import csv
import io
from datetime import UTC, date, datetime, timedelta

import pytest
from sqlalchemy import Engine, text

from app.services.analytics import safe_cell
from tests.issue_helpers import BULAWAYO, report_payload, submit
from tests.operations_helpers import Actor, assign_to_roads_officer, build_council, move


@pytest.fixture
def c(make_client):
    return build_council(make_client)


def fix(c, issue_url: str | None = None) -> None:
    url = issue_url or c["issue_url"]
    move(c["roads_officer"], url, "IN_PROGRESS")
    move(c["roads_officer"], url, "RESOLVED", note="Patched.")


def new_report(c, **overrides) -> dict:
    resident: Actor = c["resident"]
    response = submit(resident.client, resident.session, report_payload(c, **overrides))
    assert response.status_code == 201, response.text
    return response.json()


def backdate(owner_engine: Engine, issue_id: str, hours: float) -> None:
    with owner_engine.begin() as connection:
        connection.execute(
            text("UPDATE issues SET created_at = :t WHERE id = :id"),
            {"t": datetime.now(UTC) - timedelta(hours=hours), "id": issue_id},
        )


def performance(actor: Actor, c, days: int = 90):
    return actor.get(f"{c['base']}/analytics/performance?days={days}")


# --- Council performance -------------------------------------------------------------


def test_performance_reflects_the_councils_work(c, owner_engine) -> None:
    assign_to_roads_officer(c)
    fix(c)
    backdate(owner_engine, c["issue"]["id"], 10)
    new_report(c)  # waiting for review
    c["resident"].post(f"/api/v1/issues/{c['issue']['id']}/feedback", {"fixed": True})

    body = performance(c["verifier"], c).json()
    assert body["period_days"] == 90
    assert body["received"] == 2
    assert body["open_now"] == 1
    assert body["awaiting_review"] == 1
    assert body["fixed_in_period"] == 1
    for key in ("median_hours_to_first_response", "median_hours_to_verify", "median_hours_to_fix"):
        assert body[key] == pytest.approx(10, abs=0.2), key
    assert body["categories"][0] == {
        "code": "roads",
        "name": body["categories"][0]["name"],
        "received": 2,
        "fixed": 1,
    }
    assert (body["feedback_responses"], body["feedback_fixed"]) == (1, 1)
    assert {d["name"] for d in body["departments"]} == {"Roads", "Water and Sewerage"}


def test_department_backlog_counts_active_work(c, owner_engine) -> None:
    assign_to_roads_officer(c)
    backdate(owner_engine, c["issue"]["id"], 24 * 3 + 1)
    body = performance(c["admin"], c).json()
    roads = next(d for d in body["departments"] if d["name"] == "Roads")
    assert (roads["assigned"], roads["in_progress"], roads["oldest_open_days"]) == (1, 0, 3)
    water = next(d for d in body["departments"] if d["name"] == "Water and Sewerage")
    assert (water["assigned"], water["oldest_open_days"]) == (0, None)


def test_the_period_limits_what_is_counted(c, owner_engine) -> None:
    backdate(owner_engine, c["issue"]["id"], 24 * 40)
    assert performance(c["admin"], c, 30).json()["received"] == 0
    assert performance(c["admin"], c, 90).json()["received"] == 1
    assert performance(c["admin"], c, 30).json()["open_now"] == 1  # the backlog is current
    assert performance(c["admin"], c, 14).status_code == 422


def test_empty_council_has_no_medians(c, owner_engine) -> None:
    with owner_engine.begin() as connection:
        connection.execute(text("TRUNCATE issues CASCADE"))
    body = performance(c["admin"], c).json()
    assert body["received"] == 0
    assert body["median_hours_to_fix"] is None


def test_performance_is_for_this_councils_staff_only(c, make_client) -> None:
    assert performance(c["resident"], c).status_code == 403
    assert make_client().get(f"{c['base']}/analytics/performance").status_code == 401
    # Platform administrators without a membership get no operational figures.
    platform = Actor(c["platform"], c["platform_session"])
    assert performance(platform, c).status_code == 403
    other = f"/api/v1/councils/{c['bulawayo']['id']}/analytics/performance"
    assert c["admin"].get(other).status_code == 403


def test_figures_never_include_another_councils_reports(c) -> None:
    lat, lon = BULAWAYO
    new_report(c, council_id=c["bulawayo"]["id"], latitude=lat, longitude=lon)
    assert performance(c["admin"], c).json()["received"] == 1


# --- Public statistics -----------------------------------------------------------------


def public(client, query: str = "") -> dict:
    response = client.get(f"/api/v1/analytics/public{query}")
    assert response.status_code == 200, response.text
    assert "public" in response.headers["Cache-Control"]
    return response.json()


def test_public_statistics_exclude_private_and_unverified_reports(c, make_client) -> None:
    # The fixture's report is PRIVATE: verify, assign and fix it.
    assign_to_roads_officer(c)
    fix(c)
    unverified_public = new_report(c, title="Public report not yet verified")
    private_open = new_report(c, visibility="PRIVATE", title="Private report under review")
    move(c["verifier"], f"{c['base']}/issues/{private_open['id']}", "UNDER_REVIEW")
    assert unverified_public["status"] == "SUBMITTED"

    anonymous = make_client()
    body = public(anonymous)
    assert (body["published"], body["open"], body["fixed"]) == (0, 0, 0)
    assert body["categories"] == []
    assert body["councils"] == []
    assert body["median_days_to_fix"] is None
    # Signed-in staff get the same public figures here.
    assert public(c["admin"].client) == body


def test_public_statistics_count_verified_public_reports(c, make_client, owner_engine) -> None:
    report = new_report(c, title="Public pothole near the market")
    url = f"{c['base']}/issues/{report['id']}"
    move(c["verifier"], url, "UNDER_REVIEW")
    move(c["verifier"], url, "VERIFIED")
    with owner_engine.begin() as connection:
        connection.execute(
            text(
                "UPDATE issue_status_history SET created_at = now() - interval '4 days' "
                "WHERE issue_id = :id AND to_status = 'VERIFIED'"
            ),
            {"id": report["id"]},
        )
    c["roads_manager"].post(
        f"{url}/assignment",
        {"department_id": c["roads"]["id"], "assignee_user_id": c["roads_officer"].id},
    )
    fix(c, url)
    second = new_report(
        c, title="Public drain blocked by rubbish", category_id=c["categories"]["drainage"]
    )
    move(c["verifier"], f"{c['base']}/issues/{second['id']}", "UNDER_REVIEW")
    move(c["verifier"], f"{c['base']}/issues/{second['id']}", "VERIFIED")

    body = public(make_client())
    assert (body["published"], body["open"], body["fixed"]) == (2, 1, 1)
    assert body["median_days_to_fix"] == pytest.approx(4, abs=0.1)
    assert sorted((x["code"], x["received"], x["fixed"]) for x in body["categories"]) == [
        ("drainage", 1, 0),
        ("roads", 1, 1),
    ]
    [harare] = body["councils"]
    assert (harare["slug"], harare["published"], harare["open"], harare["fixed"]) == (
        "harare",
        2,
        1,
        1,
    )
    only_bulawayo = public(make_client(), f"?council_id={c['bulawayo']['id']}")
    assert only_bulawayo["published"] == 0
    for field in ("reporter", "email", "title", "latitude", "description"):
        assert field not in str(body)


# --- Export ------------------------------------------------------------------------------


def export(actor: Actor, c, start: date | None = None, end: date | None = None):
    today = datetime.now(UTC).date()
    start = start or today - timedelta(days=7)
    end = end or today
    return actor.get(f"{c['base']}/reports/export?from={start}&to={end}")


def read_csv(response) -> list[dict]:
    assert response.headers["content-type"].startswith("text/csv")
    return list(csv.DictReader(io.StringIO(response.content.decode("utf-8-sig"))))


def test_export_lists_reports_without_reporter_details(c, owner_engine) -> None:
    assign_to_roads_officer(c)
    new_report(c, title='=HYPERLINK("http://evil.example","Click")')
    response = export(c["roads_manager"], c)
    assert response.status_code == 200, response.text
    assert "attachment" in response.headers["content-disposition"]
    assert response.headers["cache-control"] == "no-store"
    rows = read_csv(response)
    assert [r["reference"] for r in rows] == sorted(r["reference"] for r in rows)
    first = rows[0]
    assert first["reference"] == c["issue"]["reference"]
    assert (first["status"], first["visibility"], first["department"]) == (
        "ASSIGNED",
        "PRIVATE",
        "Roads",
    )
    assert first["verified_at_utc"].endswith("Z") and first["fixed_at_utc"] == ""
    assert rows[1]["title"].startswith("'=HYPERLINK")
    text_body = response.text
    assert "resident@example.com" not in text_body
    assert "reporter" not in text_body

    with owner_engine.connect() as connection:
        action, details = connection.execute(
            text("SELECT action, details FROM audit_logs WHERE action = 'reports.exported'")
        ).one()
    assert details["rows"] == 2


def test_export_needs_the_export_permission(c, make_client) -> None:
    assert export(c["admin"], c).status_code == 200
    for actor in (c["verifier"], c["roads_officer"], c["resident"]):
        assert export(actor, c).status_code == 403
    assert (
        make_client().get(f"{c['base']}/reports/export?from=2026-01-01&to=2026-01-02").status_code
        == 401
    )
    other = f"/api/v1/councils/{c['bulawayo']['id']}/reports/export?from=2026-01-01&to=2026-01-02"
    assert c["admin"].get(other).status_code == 403


def test_export_only_includes_this_council_and_period(c, owner_engine) -> None:
    lat, lon = BULAWAYO
    new_report(c, council_id=c["bulawayo"]["id"], latitude=lat, longitude=lon)
    backdate(owner_engine, c["issue"]["id"], 24 * 30)
    assert read_csv(export(c["admin"], c)) == []
    today = datetime.now(UTC).date()
    rows = read_csv(export(c["admin"], c, today - timedelta(days=31), today))
    assert [r["reference"] for r in rows] == [c["issue"]["reference"]]


def test_export_rejects_bad_ranges(c) -> None:
    today = datetime.now(UTC).date()
    assert export(c["admin"], c, today, today - timedelta(days=1)).status_code == 422
    assert export(c["admin"], c, today - timedelta(days=400), today).status_code == 422
    assert c["admin"].get(f"{c['base']}/reports/export?from=yesterday&to=today").status_code == 422


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("=1+1", "'=1+1"),
        ("+27 77", "'+27 77"),
        ("-5", "'-5"),
        ("@SUM(A1)", "'@SUM(A1)"),
        ("\tcmd", "'\tcmd"),
        ("Pothole", "Pothole"),
        (None, ""),
    ],
)
def test_safe_cell_neutralises_formulas(value, expected) -> None:
    assert safe_cell(value) == expected
