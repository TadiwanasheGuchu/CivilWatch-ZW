"""Repair evidence photos added by the staff doing the work."""

import uuid

import pytest
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError

from app.core.config import get_settings
from app.core.database import bind_rls_user, get_session_factory
from tests.operations_helpers import Actor, assign_to_roads_officer, build_council, move
from tests.photo_helpers import image_bytes, jpeg_with_gps


@pytest.fixture
def c(make_client):
    return build_council(make_client)


def upload(actor: Actor, url: str, data: bytes | None = None):
    return actor.client.post(
        f"{url}/photos",
        files={"file": ("repair.jpg", data or jpeg_with_gps(), "image/jpeg")},
        headers={"X-CSRF-Token": actor.session["csrf_token"]},
    )


def test_the_assigned_officer_adds_repair_photos_while_working(c) -> None:
    assign_to_roads_officer(c)
    url = c["issue_url"]
    assert upload(c["roads_officer"], url).status_code == 409  # not started yet
    assert c["roads_officer"].get(url).json()["can_add_repair_photos"] is False
    move(c["roads_officer"], url, "IN_PROGRESS")
    assert c["roads_officer"].get(url).json()["can_add_repair_photos"] is True
    response = upload(c["roads_officer"], url)
    assert response.status_code == 201
    detail = c["roads_officer"].get(url).json()
    assert len(detail["repair_photos"]) == 1
    assert detail["photos"] == []  # report photos stay separate
    # Still allowed just after resolving; not once closed.
    move(c["roads_officer"], url, "RESOLVED", note="Patched.")
    assert upload(c["roads_officer"], url).status_code == 201
    move(c["roads_manager"], url, "CLOSED")
    assert upload(c["admin"], url).status_code == 409


def test_only_the_staff_doing_the_work_add_repair_photos(c) -> None:
    assign_to_roads_officer(c)
    move(c["roads_officer"], c["issue_url"], "IN_PROGRESS")
    for name in ("verifier", "roads_officer_2", "water_officer", "water_manager"):
        assert upload(c[name], c["issue_url"]).status_code == 403, name
    for name in ("roads_manager", "admin"):
        assert upload(c[name], c["issue_url"]).status_code == 201, name
    resident = c["resident"]
    assert upload(resident, c["issue_url"]).status_code == 403  # not council staff


def test_repair_photos_have_their_own_limit(c) -> None:
    assign_to_roads_officer(c)
    move(c["roads_officer"], c["issue_url"], "IN_PROGRESS")
    for _ in range(get_settings().photos_per_issue):
        assert upload(c["roads_officer"], c["issue_url"], image_bytes("JPEG")).status_code == 201
    over = upload(c["roads_officer"], c["issue_url"], image_bytes("JPEG"))
    assert over.status_code == 409
    assert "repair photos" in over.json()["error"]["message"]


def test_repair_photos_are_sanitised(c) -> None:
    import io
    import urllib.request

    from PIL import Image

    assign_to_roads_officer(c)
    move(c["roads_officer"], c["issue_url"], "IN_PROGRESS")
    photo = upload(c["roads_officer"], c["issue_url"]).json()
    with urllib.request.urlopen(photo["url"], timeout=5) as r:  # noqa: S310 - test storage
        assert len(Image.open(io.BytesIO(r.read())).getexif()) == 0


def test_reporter_sees_repair_photos_but_cannot_remove_them(c) -> None:
    assign_to_roads_officer(c)
    move(c["roads_officer"], c["issue_url"], "IN_PROGRESS")
    photo = upload(c["roads_officer"], c["issue_url"]).json()
    resident = c["resident"]
    own = resident.get(f"/api/v1/issues/{c['issue']['id']}").json()
    assert [p["id"] for p in own["repair_photos"]] == [photo["id"]]
    assert own["photo_count"] == 0  # list counts are report photos only
    removed = resident.client.delete(
        f"/api/v1/issues/{c['issue']['id']}/photos/{photo['id']}",
        headers={"X-CSRF-Token": resident.session["csrf_token"]},
    )
    assert removed.status_code in (404, 409)
    assert len(c["admin"].get(c["issue_url"]).json()["repair_photos"]) == 1


def test_private_report_repair_photos_stay_private(c, make_client) -> None:
    assign_to_roads_officer(c)
    move(c["roads_officer"], c["issue_url"], "IN_PROGRESS")
    upload(c["roads_officer"], c["issue_url"])
    anonymous = make_client()
    assert anonymous.get(f"/api/v1/issues/{c['issue']['id']}").status_code == 404


def test_rls_blocks_repair_photos_from_outside_the_council_and_by_reporters(c) -> None:
    assign_to_roads_officer(c)
    move(c["roads_officer"], c["issue_url"], "IN_PROGRESS")
    insert = text(
        "INSERT INTO issue_media (id, issue_id, uploaded_by_user_id, display_key, thumbnail_key, "
        "content_type, kind, width, height, byte_size, created_at) VALUES (gen_random_uuid(), "
        ":issue, :user, :d, :t, 'image/jpeg', 'repair', 1, 1, 1, now())"
    )
    for user_id in (c["resident"].id, c["platform_session"]["user"]["id"]):
        with get_session_factory()() as db:
            bind_rls_user(db, uuid.UUID(user_id))
            key = uuid.uuid4().hex
            with pytest.raises(DBAPIError, match="row-level security"):
                db.execute(
                    insert,
                    {"issue": c["issue"]["id"], "user": user_id, "d": f"{key}/d", "t": f"{key}/t"},
                )
