"""Report photos: sanitising, upload rules, and who receives photo URLs."""

import io
import os
import time
import urllib.error
import urllib.request
import uuid
from collections.abc import Callable
from urllib.parse import parse_qs, urlparse

import pytest
from fastapi.testclient import TestClient
from PIL import Image
from sqlalchemy import Engine, text
from sqlalchemy.exc import DBAPIError

from app.core.config import get_settings
from app.core.database import bind_rls_user, get_session_factory
from app.core.storage import ObjectStorage, get_storage
from tests.conftest import csrf_headers
from tests.issue_helpers import new_resident, report_payload, set_status, setup_councils, submit
from tests.photo_helpers import GPS_IFD, bomb_png, image_bytes, jpeg_with_gps


@pytest.fixture
def world(make_client: Callable[[], TestClient]):
    return setup_councils(make_client)


def upload(client: TestClient, session: dict, issue_id: str, data: bytes, name: str = "photo.jpg"):
    return client.post(
        f"/api/v1/issues/{issue_id}/photos",
        files={"file": (name, data, "image/jpeg")},
        headers=csrf_headers(session),
    )


def fetch(url: str) -> tuple[int, bytes]:
    try:
        with urllib.request.urlopen(url, timeout=5) as response:  # noqa: S310 - test-only, our storage
            return response.status, response.read()
    except urllib.error.HTTPError as error:
        return error.code, b""


@pytest.fixture
def reporter(world, make_client):
    client, session = new_resident(make_client, "reporter@example.com")
    issue = submit(client, session, report_payload(world)).json()
    return client, session, issue


# --- Sanitising ---------------------------------------------------------------------


def test_upload_strips_location_and_camera_metadata(reporter) -> None:
    client, session, issue = reporter
    original = jpeg_with_gps()
    assert Image.open(io.BytesIO(original)).getexif().get_ifd(GPS_IFD)  # sanity: GPS present

    response = upload(client, session, issue["id"], original)
    assert response.status_code == 201, response.text
    photo = response.json()
    for url in (photo["url"], photo["thumbnail_url"]):
        status, stored = fetch(url)
        assert status == 200
        image = Image.open(io.BytesIO(stored))
        assert image.format == "JPEG"
        exif = image.getexif()
        assert len(exif) == 0
        assert not exif.get_ifd(GPS_IFD)
        assert b"SecretCam" not in stored and b"PhoneMaker" not in stored
        assert "icc_profile" not in image.info


def test_camera_rotation_is_applied_before_metadata_is_removed(reporter) -> None:
    client, session, issue = reporter
    # Orientation 6: stored landscape, displayed portrait.
    photo = upload(client, session, issue["id"], jpeg_with_gps((400, 200), orientation=6)).json()
    assert (photo["width"], photo["height"]) == (200, 400)


def test_large_photos_are_resized_for_mobile_data(reporter) -> None:
    client, session, issue = reporter
    photo = upload(client, session, issue["id"], image_bytes("JPEG", (4000, 3000))).json()
    settings = get_settings()
    assert max(photo["width"], photo["height"]) == settings.photo_display_max_px
    _, thumbnail = fetch(photo["thumbnail_url"])
    assert max(Image.open(io.BytesIO(thumbnail)).size) == settings.photo_thumbnail_max_px


@pytest.mark.parametrize(("fmt", "mode"), [("PNG", "RGBA"), ("WEBP", "RGB"), ("PNG", "L")])
def test_png_and_webp_are_converted_to_jpeg(reporter, fmt, mode) -> None:
    client, session, issue = reporter
    photo = upload(client, session, issue["id"], image_bytes(fmt, mode=mode), "p.png").json()
    _, stored = fetch(photo["url"])
    assert Image.open(io.BytesIO(stored)).format == "JPEG"


@pytest.mark.parametrize(
    "data",
    [
        b"<html><script>alert(1)</script></html>",
        b"%PDF-1.4 not an image",
        b"",
        image_bytes("GIF"),
        image_bytes("BMP"),
        jpeg_with_gps()[:200],  # truncated
    ],
    ids=["html", "pdf", "empty", "gif", "bmp", "truncated"],
)
def test_files_that_are_not_accepted_photos_are_rejected(reporter, data) -> None:
    client, session, issue = reporter
    response = upload(client, session, issue["id"], data)
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "invalid_photo"


def test_content_appended_to_a_photo_is_not_stored(reporter) -> None:
    client, session, issue = reporter
    payload = b"<script>alert('stored xss')</script>"
    photo = upload(client, session, issue["id"], jpeg_with_gps() + payload).json()
    _, stored = fetch(photo["url"])
    assert payload not in stored


def test_decompression_bombs_are_rejected(reporter) -> None:
    client, session, issue = reporter
    data = bomb_png()
    assert len(data) < 200_000  # tiny on the wire
    response = upload(client, session, issue["id"], data, "bomb.png")
    assert response.status_code == 422
    assert "too large" in response.json()["error"]["message"]


def test_oversized_uploads_are_rejected(reporter) -> None:
    client, session, issue = reporter
    response = upload(
        client, session, issue["id"], os.urandom(get_settings().photo_max_upload_bytes + 1)
    )
    assert response.status_code == 413
    assert response.json()["error"]["code"] == "photo_too_large"


# --- Upload rules -----------------------------------------------------------------------


def test_upload_requires_sign_in_and_csrf(world, make_client, reporter) -> None:
    _, _, issue = reporter
    anonymous = make_client()
    files = {"file": ("p.jpg", jpeg_with_gps(), "image/jpeg")}
    assert anonymous.post(f"/api/v1/issues/{issue['id']}/photos", files=files).status_code == 401
    client, _, _ = reporter
    assert client.post(f"/api/v1/issues/{issue['id']}/photos", files=files).status_code == 403


def test_only_the_reporter_can_add_photos(world, make_client, reporter) -> None:
    _, _, issue = reporter
    other, other_session = new_resident(make_client, "other@example.com")
    response = upload(other, other_session, issue["id"], jpeg_with_gps())
    assert response.status_code == 404
    missing = upload(other, other_session, str(uuid.uuid4()), jpeg_with_gps())
    assert missing.status_code == 404


def test_photo_limit_per_report(reporter) -> None:
    client, session, issue = reporter
    for _ in range(get_settings().photos_per_issue):
        assert upload(client, session, issue["id"], image_bytes("JPEG")).status_code == 201
    response = upload(client, session, issue["id"], image_bytes("JPEG"))
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "photo_limit_reached"


def test_photos_cannot_be_added_once_the_council_has_started(reporter, owner_engine) -> None:
    client, session, issue = reporter
    set_status(owner_engine, issue["id"], "UNDER_REVIEW")
    response = upload(client, session, issue["id"], image_bytes("JPEG"))
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "report_locked"


def test_storage_outage_fails_cleanly(reporter, owner_engine: Engine) -> None:
    client, session, issue = reporter
    broken = ObjectStorage(
        get_settings().model_copy(update={"storage_endpoint_url": "http://127.0.0.1:1"})
    )
    client.app.dependency_overrides[get_storage] = lambda: broken
    try:
        response = upload(client, session, issue["id"], image_bytes("JPEG"))
    finally:
        client.app.dependency_overrides.clear()
    assert response.status_code == 503
    with owner_engine.connect() as connection:
        assert connection.scalar(text("SELECT count(*) FROM issue_media")) == 0


# --- Who receives photo URLs -------------------------------------------------------------------


def test_reporter_sees_their_photos_with_short_lived_urls(reporter) -> None:
    client, session, issue = reporter
    upload(client, session, issue["id"], jpeg_with_gps())
    detail = client.get(f"/api/v1/issues/{issue['id']}").json()
    assert len(detail["photos"]) == 1
    query = parse_qs(urlparse(detail["photos"][0]["url"]).query)
    assert query["X-Amz-Expires"] == [str(get_settings().media_url_ttl_seconds)]
    assert "X-Amz-Signature" in query
    mine = client.get("/api/v1/issues/mine").json()["items"][0]
    assert mine["photo_count"] == 1
    assert mine["cover_thumbnail_url"]


def test_photos_of_unpublished_or_private_reports_reach_no_one_else(
    world, make_client, owner_engine
) -> None:
    owner, owner_session = new_resident(make_client, "owner@example.com")
    private = submit(owner, owner_session, report_payload(world, visibility="PRIVATE")).json()
    unverified = submit(owner, owner_session, report_payload(world)).json()
    for issue in (private, unverified):
        upload(owner, owner_session, issue["id"], jpeg_with_gps())
    set_status(owner_engine, private["id"], "VERIFIED")

    stranger = make_client()
    other, _ = new_resident(make_client, "other@example.com")
    for client in (stranger, other):
        listing = client.get("/api/v1/issues")
        assert "X-Amz-Signature" not in listing.text
        for issue in (private, unverified):
            response = client.get(f"/api/v1/issues/{issue['id']}")
            assert response.status_code == 404
            assert "X-Amz" not in response.text


def test_published_public_report_shows_photos_to_everyone(world, make_client, owner_engine) -> None:
    owner, owner_session = new_resident(make_client, "owner@example.com")
    issue = submit(owner, owner_session, report_payload(world)).json()
    upload(owner, owner_session, issue["id"], jpeg_with_gps())
    set_status(owner_engine, issue["id"], "VERIFIED")

    anonymous = make_client()
    detail = anonymous.get(f"/api/v1/issues/{issue['id']}").json()
    assert len(detail["photos"]) == 1
    status, _ = fetch(detail["photos"][0]["url"])
    assert status == 200
    item = anonymous.get("/api/v1/issues").json()["items"][0]
    assert item["photo_count"] == 1 and item["cover_thumbnail_url"]


def test_no_permanent_or_unsigned_urls_are_ever_returned(world, make_client, owner_engine) -> None:
    owner, owner_session = new_resident(make_client, "owner@example.com")
    issue = submit(owner, owner_session, report_payload(world)).json()
    photo = upload(owner, owner_session, issue["id"], jpeg_with_gps()).json()
    for url in (photo["url"], photo["thumbnail_url"]):
        query = parse_qs(urlparse(url).query)
        assert {"X-Amz-Signature", "X-Amz-Expires", "X-Amz-Credential"} <= set(query)
        assert int(query["X-Amz-Expires"][0]) <= 3600


# --- Database rules (as the API role) ------------------------------------------------------------


def test_only_the_reporter_can_insert_media_rows(world, make_client) -> None:
    owner, owner_session = new_resident(make_client, "owner@example.com")
    issue = submit(owner, owner_session, report_payload(world)).json()
    _, other_session = new_resident(make_client, "other@example.com")
    with get_session_factory()() as db:
        bind_rls_user(db, uuid.UUID(other_session["user"]["id"]))
        with pytest.raises(DBAPIError, match="row-level security"):
            db.execute(
                text(
                    "INSERT INTO issue_media (id, issue_id, uploaded_by_user_id, display_key, "
                    "thumbnail_key, content_type, width, height, byte_size, created_at) VALUES "
                    "(gen_random_uuid(), :issue, :user, 'x/d.jpg', 'x/t.jpg', 'image/jpeg', "
                    "1, 1, 1, now())"
                ),
                {"issue": issue["id"], "user": other_session["user"]["id"]},
            )


# --- Storage enforcement (needs a real S3-compatible service, e.g. MinIO in CI) ------------------

enforces_auth = pytest.mark.skipif(
    os.environ.get("CIVICWATCH_TEST_STORAGE_ENFORCES_AUTH") != "1",
    reason="needs real S3-compatible storage that enforces signatures (CI runs MinIO)",
)


@enforces_auth
def test_private_media_cannot_be_fetched_without_a_valid_signature(reporter) -> None:
    client, session, issue = reporter
    photo = upload(client, session, issue["id"], jpeg_with_gps()).json()
    unsigned = photo["url"].split("?", 1)[0]
    assert fetch(unsigned)[0] == 403
    tampered = photo["url"].replace("X-Amz-Signature=", "X-Amz-Signature=0")
    assert fetch(tampered)[0] == 403
    assert fetch(photo["url"])[0] == 200


@enforces_auth
def test_signed_urls_expire(reporter) -> None:
    client, session, issue = reporter
    upload(client, session, issue["id"], jpeg_with_gps())
    with get_session_factory()() as db:
        bind_rls_user(db, uuid.UUID(session["user"]["id"]))
        media_key = db.scalar(text("SELECT display_key FROM issue_media"))
    short_lived = get_storage().signed_url(media_key, ttl_seconds=1)
    assert fetch(short_lived)[0] == 200
    time.sleep(2)
    assert fetch(short_lived)[0] == 403


# --- Removing a photo ---------------------------------------------------------------------------


def test_reporter_can_remove_a_photo_before_review(reporter) -> None:
    client, session, issue = reporter
    photo = upload(client, session, issue["id"], jpeg_with_gps()).json()
    response = client.delete(
        f"/api/v1/issues/{issue['id']}/photos/{photo['id']}", headers=csrf_headers(session)
    )
    assert response.status_code == 204
    assert client.get(f"/api/v1/issues/{issue['id']}").json()["photos"] == []
    # The stored objects are gone too.
    assert fetch(photo["url"])[0] == 404


def test_photo_removal_rules(world, make_client, reporter, owner_engine) -> None:
    client, session, issue = reporter
    photo = upload(client, session, issue["id"], jpeg_with_gps()).json()
    url = f"/api/v1/issues/{issue['id']}/photos/{photo['id']}"

    assert client.delete(url).status_code == 403  # CSRF
    other, other_session = new_resident(make_client, "other@example.com")
    assert other.delete(url, headers=csrf_headers(other_session)).status_code == 404
    missing = f"/api/v1/issues/{issue['id']}/photos/{uuid.uuid4()}"
    assert client.delete(missing, headers=csrf_headers(session)).status_code == 404

    set_status(owner_engine, issue["id"], "UNDER_REVIEW")
    locked = client.delete(url, headers=csrf_headers(session))
    assert locked.status_code == 409
    assert locked.json()["error"]["code"] == "report_locked"


def test_rls_blocks_deleting_photos_of_reviewed_or_others_reports(
    world, make_client, reporter, owner_engine
) -> None:
    client, session, issue = reporter
    upload(client, session, issue["id"], jpeg_with_gps())
    _, other_session = new_resident(make_client, "other@example.com")
    with get_session_factory()() as db:
        bind_rls_user(db, uuid.UUID(other_session["user"]["id"]))
        assert db.execute(text("DELETE FROM issue_media")).rowcount == 0
        db.rollback()
    set_status(owner_engine, issue["id"], "UNDER_REVIEW")
    with get_session_factory()() as db:
        bind_rls_user(db, uuid.UUID(session["user"]["id"]))
        assert db.execute(text("DELETE FROM issue_media")).rowcount == 0
        db.rollback()
