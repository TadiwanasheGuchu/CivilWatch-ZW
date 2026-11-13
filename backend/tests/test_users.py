"""The signed-in user's own account."""

from collections.abc import Callable

from fastapi.testclient import TestClient

from tests.conftest import DEFAULT_PASSWORD, csrf_headers, register

NEW_PASSWORD = "a brand new passphrase"


def test_me_requires_sign_in(client: TestClient) -> None:
    assert client.get("/api/v1/users/me").status_code == 401


def test_me_returns_own_profile_only(client: TestClient) -> None:
    body = register(client, email="me@example.com", full_name="Nyasha Dube")
    response = client.get("/api/v1/users/me")
    assert response.status_code == 200
    assert response.json() == body["user"]
    assert "password_hash" not in response.text


def test_update_profile(client: TestClient) -> None:
    body = register(client)
    response = client.patch(
        "/api/v1/users/me", json={"full_name": "Tendai  Chikomo"}, headers=csrf_headers(body)
    )
    assert response.status_code == 200
    assert response.json()["full_name"] == "Tendai Chikomo"


def test_update_profile_requires_csrf(client: TestClient) -> None:
    register(client)
    response = client.patch("/api/v1/users/me", json={"full_name": "Changed"})
    assert response.status_code == 403


def test_profile_update_cannot_escalate_privileges(client: TestClient) -> None:
    body = register(client)
    response = client.patch(
        "/api/v1/users/me",
        json={"full_name": "X", "is_platform_admin": True},
        headers=csrf_headers(body),
    )
    assert response.status_code == 422
    assert client.get("/api/v1/users/me").json()["is_platform_admin"] is False


def test_change_password_signs_out_other_sessions(
    client: TestClient, make_client: Callable[[], TestClient]
) -> None:
    body = register(client, email="mover@example.com")
    phone = make_client()
    phone.post(
        "/api/v1/auth/login", json={"email": "mover@example.com", "password": DEFAULT_PASSWORD}
    )
    assert phone.get("/api/v1/users/me").status_code == 200

    response = client.post(
        "/api/v1/users/me/password",
        json={"current_password": DEFAULT_PASSWORD, "new_password": NEW_PASSWORD},
        headers=csrf_headers(body),
    )
    assert response.status_code == 204
    assert client.get("/api/v1/users/me").status_code == 200
    assert phone.get("/api/v1/users/me").status_code == 401

    fresh = make_client()
    old = {"email": "mover@example.com", "password": DEFAULT_PASSWORD}
    new = {"email": "mover@example.com", "password": NEW_PASSWORD}
    assert fresh.post("/api/v1/auth/login", json=old).status_code == 401
    assert fresh.post("/api/v1/auth/login", json=new).status_code == 200


def test_change_password_requires_correct_current_password(client: TestClient) -> None:
    body = register(client)
    response = client.post(
        "/api/v1/users/me/password",
        json={"current_password": "not my password", "new_password": NEW_PASSWORD},
        headers=csrf_headers(body),
    )
    assert response.status_code == 400
    assert response.json()["error"]["code"] == "invalid_current_password"
    # A wrong current password does not sign the user out.
    assert client.get("/api/v1/users/me").status_code == 200


def test_change_password_guessing_is_rate_limited(client: TestClient) -> None:
    body = register(client)
    statuses = [
        client.post(
            "/api/v1/users/me/password",
            json={"current_password": f"guess number {i}", "new_password": NEW_PASSWORD},
            headers=csrf_headers(body),
        ).status_code
        for i in range(6)
    ]
    assert statuses[:5] == [400] * 5
    assert statuses[5] == 429


def test_new_password_must_differ_and_be_valid(client: TestClient) -> None:
    body = register(client)
    for new_password in (DEFAULT_PASSWORD, "short"):
        response = client.post(
            "/api/v1/users/me/password",
            json={"current_password": DEFAULT_PASSWORD, "new_password": new_password},
            headers=csrf_headers(body),
        )
        assert response.status_code == 422
