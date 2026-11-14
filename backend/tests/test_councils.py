"""Council directory, creation, workspaces and staff management."""

from collections.abc import Callable

from fastapi.testclient import TestClient

from app.models.councils import CouncilRole
from tests.conftest import (
    add_member,
    create_council,
    csrf_headers,
    make_platform_admin,
    register,
    sign_in,
)

ADMIN = CouncilRole.COUNCIL_ADMIN
OFFICER = CouncilRole.VERIFICATION_OFFICER


def setup_council(make_client: Callable[[], TestClient], slug: str = "harare"):
    """Platform admin creates a council and appoints its first administrator."""
    platform = make_client()
    platform_session = make_platform_admin(platform, "platform@example.com")
    council = create_council(platform, platform_session, slug)
    council_admin = make_client()
    register(council_admin, email=f"admin@{slug}.example.com", full_name=f"{slug} Admin")
    assert (
        add_member(
            platform, platform_session, council["id"], f"admin@{slug}.example.com", ADMIN
        ).status_code
        == 201
    )
    admin_session = sign_in(council_admin, f"admin@{slug}.example.com")
    return platform, platform_session, council, council_admin, admin_session


# --- Directory and creation -------------------------------------------------------


def test_public_directory_needs_no_account(
    client: TestClient, make_client: Callable[[], TestClient]
) -> None:
    platform = make_client()
    session = make_platform_admin(platform, "platform@example.com")
    create_council(platform, session, "harare", "Harare City Council")
    create_council(platform, session, "bulawayo", "Bulawayo City Council")
    response = client.get("/api/v1/councils?page_size=1")
    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 2
    assert [c["slug"] for c in body["items"]] == ["bulawayo"]
    assert set(body["items"][0]) == {"id", "slug", "name"}


def test_only_platform_admins_can_create_councils(client: TestClient) -> None:
    resident = register(client)
    response = client.post(
        "/api/v1/councils",
        json={"slug": "mutare", "name": "Mutare"},
        headers=csrf_headers(resident),
    )
    assert response.status_code == 403


def test_council_creation_requires_sign_in_and_csrf(client: TestClient) -> None:
    assert client.post("/api/v1/councils", json={"slug": "a-b", "name": "A"}).status_code == 401
    make_platform_admin(client, "platform@example.com")
    assert client.post("/api/v1/councils", json={"slug": "a-b", "name": "A"}).status_code == 403


def test_council_slug_rules(client: TestClient) -> None:
    session = make_platform_admin(client, "platform@example.com")
    for slug in ("Ha", "harare city", "-harare", "harare--city", "ha_rare"):
        response = client.post(
            "/api/v1/councils", json={"slug": slug, "name": "X"}, headers=csrf_headers(session)
        )
        assert response.status_code == 422, slug
    create_council(client, session, "harare")
    duplicate = client.post(
        "/api/v1/councils",
        json={"slug": "HARARE", "name": "Other"},
        headers=csrf_headers(session),
    )
    assert duplicate.status_code == 409


# --- Workspaces --------------------------------------------------------------------------


def test_member_workspace_lists_role_and_permissions(
    make_client: Callable[[], TestClient],
) -> None:
    _, _, council, admin, _ = setup_council(make_client)
    body = admin.get(f"/api/v1/councils/{council['id']}/workspace").json()
    assert body["role"] == "council_admin"
    assert body["via_platform_admin"] is False
    assert set(body["permissions"]) == {
        "workspace.view",
        "members.view",
        "members.manage",
        "audit.view",
    }


def test_resident_has_no_workspace(make_client: Callable[[], TestClient]) -> None:
    _, _, council, _, _ = setup_council(make_client)
    resident = make_client()
    register(resident, email="resident@example.com")
    for path in ("workspace", "members", "audit-logs"):
        response = resident.get(f"/api/v1/councils/{council['id']}/{path}")
        assert response.status_code == 403, path


def test_unknown_council_is_404(client: TestClient) -> None:
    register(client)
    response = client.get("/api/v1/councils/00000000-0000-0000-0000-000000000000/workspace")
    assert response.status_code == 404


def test_platform_admin_without_membership_gets_no_operational_access(
    make_client: Callable[[], TestClient],
) -> None:
    platform, _, council, _, _ = setup_council(make_client)
    body = platform.get(f"/api/v1/councils/{council['id']}/workspace").json()
    assert body["role"] is None
    assert body["via_platform_admin"] is True
    assert "workspace.view" not in body["permissions"]


def test_my_memberships_lists_only_active_own_workspaces(
    make_client: Callable[[], TestClient],
) -> None:
    platform, platform_session, harare, admin, admin_session = setup_council(make_client)
    bulawayo = create_council(platform, platform_session, "bulawayo")
    add_member(platform, platform_session, bulawayo["id"], "admin@harare.example.com", OFFICER)
    memberships = admin.get("/api/v1/users/me/memberships").json()
    assert sorted((m["council"]["slug"], m["role"]) for m in memberships) == [
        ("bulawayo", "verification_officer"),
        ("harare", "council_admin"),
    ]
    resident = make_client()
    register(resident, email="resident@example.com")
    assert resident.get("/api/v1/users/me/memberships").json() == []


# --- Staff management ------------------------------------------------------------------------


def test_council_admin_manages_staff(make_client: Callable[[], TestClient]) -> None:
    _, _, council, admin, admin_session = setup_council(make_client)
    officer = make_client()
    register(officer, email="officer@example.com", full_name="Rumbi Officer")

    added = add_member(admin, admin_session, council["id"], "OFFICER@example.com", OFFICER)
    assert added.status_code == 201
    member = added.json()
    assert member["full_name"] == "Rumbi Officer"
    assert member["role"] == "verification_officer"

    listing = admin.get(f"/api/v1/councils/{council['id']}/members").json()
    assert listing["total"] == 2

    changed = admin.patch(
        f"/api/v1/councils/{council['id']}/members/{member['membership_id']}",
        json={"role": "maintenance_officer"},
        headers=csrf_headers(admin_session),
    )
    assert changed.status_code == 200
    assert changed.json()["role"] == "maintenance_officer"

    assert officer.get(f"/api/v1/councils/{council['id']}/workspace").status_code == 200
    removed = admin.delete(
        f"/api/v1/councils/{council['id']}/members/{member['membership_id']}",
        headers=csrf_headers(admin_session),
    )
    assert removed.status_code == 204
    # Access ends immediately, without signing the officer out.
    assert officer.get(f"/api/v1/councils/{council['id']}/workspace").status_code == 403
    assert officer.get("/api/v1/users/me").status_code == 200

    # The person can be re-appointed later; the old membership stays as history.
    again = add_member(admin, admin_session, council["id"], "officer@example.com", OFFICER)
    assert again.status_code == 201
    assert again.json()["membership_id"] != member["membership_id"]


def test_add_member_errors(make_client: Callable[[], TestClient]) -> None:
    _, _, council, admin, admin_session = setup_council(make_client)
    unknown = add_member(admin, admin_session, council["id"], "nobody@example.com", OFFICER)
    assert unknown.status_code == 404
    duplicate = add_member(admin, admin_session, council["id"], "admin@harare.example.com", OFFICER)
    assert duplicate.status_code == 409
    bad_role = add_member(admin, admin_session, council["id"], "admin@harare.example.com", "mayor")
    assert bad_role.status_code == 422
    resident_role = add_member(
        admin, admin_session, council["id"], "admin@harare.example.com", "resident"
    )
    assert resident_role.status_code == 422


def test_staff_without_manage_permission_cannot_change_staff(
    make_client: Callable[[], TestClient],
) -> None:
    _, _, council, admin, admin_session = setup_council(make_client)
    officer = make_client()
    register(officer, email="officer@example.com")
    add_member(admin, admin_session, council["id"], "officer@example.com", OFFICER)
    officer_session = sign_in(officer, "officer@example.com")
    register(make_client(), email="friend@example.com")

    assert officer.get(f"/api/v1/councils/{council['id']}/members").status_code == 200
    escalate = add_member(officer, officer_session, council["id"], "friend@example.com", ADMIN)
    assert escalate.status_code == 403
    admin_membership = admin.get(f"/api/v1/councils/{council['id']}/members").json()["items"]
    own = next(m for m in admin_membership if m["user_id"] == officer_session["user"]["id"])
    self_promote = officer.patch(
        f"/api/v1/councils/{council['id']}/members/{own['membership_id']}",
        json={"role": "council_admin"},
        headers=csrf_headers(officer_session),
    )
    assert self_promote.status_code == 403
    assert officer.get(f"/api/v1/councils/{council['id']}/audit-logs").status_code == 403


def test_last_council_admin_cannot_be_removed_or_demoted(
    make_client: Callable[[], TestClient],
) -> None:
    _, _, council, admin, admin_session = setup_council(make_client)
    own_id = admin.get(f"/api/v1/councils/{council['id']}/members").json()["items"][0][
        "membership_id"
    ]
    url = f"/api/v1/councils/{council['id']}/members/{own_id}"
    demote = admin.patch(
        url, json={"role": "maintenance_officer"}, headers=csrf_headers(admin_session)
    )
    assert demote.status_code == 409
    assert demote.json()["error"]["code"] == "last_council_admin"
    assert admin.delete(url, headers=csrf_headers(admin_session)).status_code == 409

    register(make_client(), email="second@example.com")
    add_member(admin, admin_session, council["id"], "second@example.com", ADMIN)
    assert admin.delete(url, headers=csrf_headers(admin_session)).status_code == 204


def test_staff_changes_are_audited(make_client: Callable[[], TestClient]) -> None:
    _, _, council, admin, admin_session = setup_council(make_client)
    register(make_client(), email="officer@example.com")
    add_member(admin, admin_session, council["id"], "officer@example.com", OFFICER)

    entries = admin.get(f"/api/v1/councils/{council['id']}/audit-logs").json()["items"]
    actions = [e["action"] for e in entries]
    assert actions == ["membership.granted", "membership.granted", "council.created"]
    latest = entries[0]
    assert latest["actor_user_id"] == admin_session["user"]["id"]
    assert latest["actor_name"] == "harare Admin"
    assert entries[1]["actor_name"] == "Platform Admin"
    assert latest["details"]["role"] == "verification_officer"
    assert latest["details"]["via_platform_admin"] is False
    assert latest["request_id"]
    # The first administrator was appointed by the platform admin, and it says so.
    assert entries[1]["details"]["via_platform_admin"] is True
