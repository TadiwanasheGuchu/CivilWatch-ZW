"""Shared setup for report tests."""

from collections.abc import Callable
from typing import Any

from fastapi.testclient import TestClient
from sqlalchemy import Engine, text

from tests.conftest import create_council, csrf_headers, make_platform_admin, register

# Harare city centre, and a point in Bulawayo.
HARARE = (-17.8292, 31.0522)
BULAWAYO = (-20.1325, 28.6265)


def setup_councils(make_client: Callable[[], TestClient]) -> dict[str, Any]:
    platform = make_client()
    session = make_platform_admin(platform, "platform@example.com")
    harare = create_council(platform, session, "harare", "Harare City Council")
    bulawayo = create_council(platform, session, "bulawayo", "Bulawayo City Council")
    categories = {c["code"]: c["id"] for c in platform.get("/api/v1/categories").json()}
    return {
        "platform": platform,
        "platform_session": session,
        "harare": harare,
        "bulawayo": bulawayo,
        "categories": categories,
    }


def report_payload(world: dict[str, Any], **overrides: Any) -> dict[str, Any]:
    lat, lon = HARARE
    payload = {
        "council_id": world["harare"]["id"],
        "category_id": world["categories"]["roads"],
        "title": "Large pothole on Samora Machel Avenue",
        "description": "Deep pothole in the left lane, cars swerve to avoid it.",
        "latitude": lat,
        "longitude": lon,
        "location_description": "Outside the main post office",
        "visibility": "PUBLIC",
    }
    payload.update(overrides)
    return payload


def new_resident(make_client: Callable[[], TestClient], email: str) -> tuple[TestClient, dict]:
    client = make_client()
    session = register(client, email=email)
    return client, session


def submit(client: TestClient, session: dict, payload: dict) -> Any:
    return client.post("/api/v1/issues", json=payload, headers=csrf_headers(session))


def set_status(owner_engine: Engine, issue_id: str, status: str) -> None:
    """Test setup only: council workflow endpoints arrive in Milestone 3."""
    with owner_engine.begin() as connection:
        connection.execute(
            text("UPDATE issues SET status = :status WHERE id = :id"),
            {"status": status, "id": issue_id},
        )
