"""Registration, sign-in, sessions and CSRF (CLAUDE.md §15 priority 1)."""

import logging
from collections.abc import Callable
from datetime import UTC, datetime, timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models.identity import User, UserSession
from tests.conftest import DEFAULT_PASSWORD, csrf_headers, register

COOKIE = get_settings().session_cookie_name


def login(client: TestClient, email: str, password: str = DEFAULT_PASSWORD):
    return client.post("/api/v1/auth/login", json={"email": email, "password": password})


# --- Registration -------------------------------------------------------------


def test_register_creates_account_and_signs_in(client: TestClient) -> None:
    body = register(client, email="Tendai@Example.com", full_name="  Tendai   Moyo ")
    assert body["user"]["email"] == "tendai@example.com"
    assert body["user"]["full_name"] == "Tendai Moyo"
    assert body["user"]["is_platform_admin"] is False
    assert len(body["csrf_token"]) >= 40
    assert "password" not in str(body).lower()
    assert client.get("/api/v1/auth/session").status_code == 200


def test_session_cookie_is_hardened(client: TestClient) -> None:
    response = client.post(
        "/api/v1/auth/register",
        json={"email": "a@example.com", "password": DEFAULT_PASSWORD, "full_name": "A"},
    )
    cookie = response.headers["set-cookie"]
    assert cookie.startswith(f"{COOKIE}=")
    lowered = cookie.lower()
    for attribute in ("httponly", "secure", "samesite=lax", "path=/"):
        assert attribute in lowered
    assert "domain=" not in lowered


def test_password_is_stored_as_argon2id_hash(client: TestClient, db: Session) -> None:
    register(client)
    stored = db.scalar(select(User.password_hash))
    assert stored is not None
    assert stored.startswith("$argon2id$")
    assert DEFAULT_PASSWORD not in stored


def test_session_token_is_stored_only_as_hash(client: TestClient, db: Session) -> None:
    register(client)
    token = client.cookies.get(COOKIE)
    assert token
    session = db.scalar(select(UserSession))
    assert session is not None
    assert token.encode() != session.token_hash
    assert len(session.token_hash) == 32


def test_duplicate_email_is_rejected_case_insensitively(client: TestClient) -> None:
    register(client, email="rudo@example.com")
    response = client.post(
        "/api/v1/auth/register",
        json={"email": "RUDO@example.com", "password": DEFAULT_PASSWORD, "full_name": "R"},
    )
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "conflict"


@pytest.mark.parametrize(
    "payload",
    [
        {"email": "x@example.com", "password": "short", "full_name": "X"},
        {"email": "x@example.com", "password": "a" * 129, "full_name": "X"},
        {"email": "x@example.com", "password": " " * 12, "full_name": "X"},
        {"email": "x@example.com", "password": "x@example.com", "full_name": "X"},
        {"email": "not-an-email", "password": DEFAULT_PASSWORD, "full_name": "X"},
        {"email": "x@example.com", "password": DEFAULT_PASSWORD, "full_name": "   "},
        {"email": "x@example.com", "password": DEFAULT_PASSWORD, "full_name": "A\x00B"},
        {
            "email": "x@example.com",
            "password": DEFAULT_PASSWORD,
            "full_name": "X",
            "is_platform_admin": True,
        },
    ],
)
def test_invalid_registration_is_rejected(client: TestClient, payload: dict) -> None:
    response = client.post("/api/v1/auth/register", json=payload)
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "validation_error"
    # Validation errors never echo the submitted values back.
    assert payload["password"] not in response.text


def test_registration_is_rate_limited_per_ip(client: TestClient) -> None:
    limit = get_settings().registrations_per_ip
    for index in range(limit):
        register(client, email=f"user{index}@example.com")
    response = client.post(
        "/api/v1/auth/register",
        json={"email": "late@example.com", "password": DEFAULT_PASSWORD, "full_name": "L"},
    )
    assert response.status_code == 429
    assert int(response.headers["Retry-After"]) > 0


# --- Sign-in ------------------------------------------------------------------


def test_login_succeeds_with_correct_credentials(
    client: TestClient, make_client: Callable[[], TestClient]
) -> None:
    register(client, email="chipo@example.com")
    other_browser = make_client()
    response = login(other_browser, "CHIPO@example.com")
    assert response.status_code == 200
    assert response.json()["user"]["email"] == "chipo@example.com"
    assert other_browser.get("/api/v1/users/me").status_code == 200


def test_wrong_password_and_unknown_email_get_identical_responses(
    client: TestClient, make_client: Callable[[], TestClient]
) -> None:
    register(client, email="chipo@example.com")
    browser = make_client()
    wrong_password = login(browser, "chipo@example.com", "not the password")
    unknown_email = login(browser, "nobody@example.com")
    assert wrong_password.status_code == unknown_email.status_code == 401
    assert wrong_password.json()["error"]["message"] == unknown_email.json()["error"]["message"]
    assert COOKIE not in wrong_password.cookies


def test_inactive_user_cannot_sign_in_and_existing_sessions_stop_working(
    client: TestClient, make_client: Callable[[], TestClient], db: Session
) -> None:
    register(client, email="gone@example.com")
    db.execute(update(User).values(is_active=False))
    db.commit()
    assert client.get("/api/v1/auth/session").status_code == 401
    assert login(make_client(), "gone@example.com").status_code == 401


def test_account_locks_after_repeated_failures(
    client: TestClient, make_client: Callable[[], TestClient]
) -> None:
    register(client, email="target@example.com")
    attacker = make_client()
    for _ in range(get_settings().login_failures_per_account):
        assert login(attacker, "target@example.com", "guess guess guess").status_code == 401
    # Even the correct password is refused while the account is locked.
    locked = login(attacker, "target@example.com")
    assert locked.status_code == 429
    assert locked.json()["error"]["code"] == "rate_limited"
    assert int(locked.headers["Retry-After"]) > 0


def test_successful_login_resets_failure_count(
    client: TestClient, make_client: Callable[[], TestClient]
) -> None:
    register(client, email="forgetful@example.com")
    browser = make_client()
    failures = get_settings().login_failures_per_account
    for _ in range(failures - 1):
        login(browser, "forgetful@example.com", "wrong password")
    assert login(browser, "forgetful@example.com").status_code == 200
    for _ in range(failures - 1):
        assert login(browser, "forgetful@example.com", "wrong password").status_code == 401
    assert login(browser, "forgetful@example.com").status_code == 200


def test_signing_in_again_revokes_the_previous_session(client: TestClient, db: Session) -> None:
    register(client, email="again@example.com")
    first_token = client.cookies.get(COOKIE)
    assert login(client, "again@example.com").status_code == 200
    assert client.cookies.get(COOKIE) != first_token
    sessions = db.scalars(select(UserSession).order_by(UserSession.created_at)).all()
    assert len(sessions) == 2
    assert sessions[0].revoked_at is not None
    assert sessions[1].revoked_at is None


def test_credentials_are_never_logged(client: TestClient, caplog: pytest.LogCaptureFixture) -> None:
    caplog.set_level(logging.DEBUG)
    register(client, email="private@example.com")
    login(client, "private@example.com")
    token = client.cookies.get(COOKIE)
    assert token
    assert DEFAULT_PASSWORD not in caplog.text
    assert token not in caplog.text
    assert "private@example.com" not in caplog.text


# --- Session lifecycle ----------------------------------------------------------


def test_session_endpoint_requires_a_session(client: TestClient) -> None:
    response = client.get("/api/v1/auth/session")
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "authentication_required"


def test_forged_session_cookie_is_rejected(client: TestClient) -> None:
    client.cookies.set(COOKIE, "forged-token-value", domain="testserver.local")
    assert client.get("/api/v1/auth/session").status_code == 401


def test_logout_revokes_session_server_side(client: TestClient) -> None:
    body = register(client)
    token = client.cookies.get(COOKIE)
    response = client.post("/api/v1/auth/logout", headers=csrf_headers(body))
    assert response.status_code == 204
    assert "max-age=0" in response.headers["set-cookie"].lower()
    # Replaying the old cookie (e.g. stolen before logout) no longer works.
    client.cookies.set(COOKIE, token, domain="testserver.local")
    assert client.get("/api/v1/auth/session").status_code == 401


def test_absolute_expiry_is_enforced(client: TestClient, db: Session) -> None:
    register(client)
    db.execute(update(UserSession).values(expires_at=datetime.now(UTC) - timedelta(seconds=1)))
    db.commit()
    assert client.get("/api/v1/auth/session").status_code == 401


def test_idle_timeout_is_enforced(client: TestClient, db: Session) -> None:
    register(client)
    idle = timedelta(minutes=get_settings().session_idle_timeout_minutes, seconds=1)
    db.execute(update(UserSession).values(last_seen_at=datetime.now(UTC) - idle))
    db.commit()
    assert client.get("/api/v1/auth/session").status_code == 401


def test_activity_extends_idle_window(client: TestClient, db: Session) -> None:
    register(client)
    stale = datetime.now(UTC) - timedelta(hours=1)
    db.execute(update(UserSession).values(last_seen_at=stale))
    db.commit()
    assert client.get("/api/v1/auth/session").status_code == 200
    db.expire_all()
    assert db.scalar(select(UserSession.last_seen_at)) > stale


# --- CSRF and cross-origin protection ----------------------------------------------


def test_state_change_without_csrf_token_is_rejected(client: TestClient) -> None:
    register(client)
    response = client.post("/api/v1/auth/logout")
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "csrf_token_invalid"
    assert client.get("/api/v1/auth/session").status_code == 200


def test_csrf_token_from_another_session_is_rejected(
    client: TestClient, make_client: Callable[[], TestClient]
) -> None:
    register(client, email="victim@example.com")
    attacker_body = register(make_client(), email="attacker@example.com")
    response = client.post("/api/v1/auth/logout", headers=csrf_headers(attacker_body))
    assert response.status_code == 403


def test_cross_origin_login_is_rejected(client: TestClient) -> None:
    register(client, email="victim@example.com")
    response = client.post(
        "/api/v1/auth/login",
        json={"email": "victim@example.com", "password": DEFAULT_PASSWORD},
        headers={"Origin": "https://evil.example"},
    )
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "origin_not_allowed"


def test_allowed_origin_can_sign_in(client: TestClient) -> None:
    register(client, email="web@example.com")
    response = client.post(
        "/api/v1/auth/login",
        json={"email": "web@example.com", "password": DEFAULT_PASSWORD},
        headers={"Origin": "http://localhost:3000"},
    )
    assert response.status_code == 200
