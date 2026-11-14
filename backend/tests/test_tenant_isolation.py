"""Cross-council isolation (CLAUDE.md §7, §15). Council A's staff must not
see or change anything belonging to council B through any endpoint."""

from collections.abc import Callable

import pytest
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


@pytest.fixture
def two_councils(make_client: Callable[[], TestClient]):
    platform = make_client()
    platform_session = make_platform_admin(platform, "platform@example.com")
    harare = create_council(platform, platform_session, "harare")
    bulawayo = create_council(platform, platform_session, "bulawayo")
    clients = {}
    for slug, council in (("harare", harare), ("bulawayo", bulawayo)):
        client = make_client()
        email = f"admin@{slug}.example.com"
        register(client, email=email)
        add_member(platform, platform_session, council["id"], email, CouncilRole.COUNCIL_ADMIN)
        clients[slug] = (client, sign_in(client, email))
    register(make_client(), email="officer@bulawayo.example.com")
    b_client, b_session = clients["bulawayo"]
    b_officer = add_member(
        b_client,
        b_session,
        bulawayo["id"],
        "officer@bulawayo.example.com",
        CouncilRole.MAINTENANCE_OFFICER,
    ).json()
    return {"harare": harare, "bulawayo": bulawayo, "clients": clients, "b_officer": b_officer}


def test_council_a_admin_cannot_read_council_b(two_councils) -> None:
    a_client, _ = two_councils["clients"]["harare"]
    b_id = two_councils["bulawayo"]["id"]
    for path in ("workspace", "members", "audit-logs"):
        response = a_client.get(f"/api/v1/councils/{b_id}/{path}")
        assert response.status_code == 403, path
        assert "officer@bulawayo" not in response.text


def test_council_a_admin_cannot_change_council_b_staff(two_councils) -> None:
    a_client, a_session = two_councils["clients"]["harare"]
    b_id = two_councils["bulawayo"]["id"]
    officer_id = two_councils["b_officer"]["membership_id"]
    register(a_client, email="spy@example.com")  # any registered account
    a_session = sign_in(a_client, "admin@harare.example.com")

    assert (
        add_member(
            a_client, a_session, b_id, "spy@example.com", CouncilRole.COUNCIL_ADMIN
        ).status_code
        == 403
    )
    url = f"/api/v1/councils/{b_id}/members/{officer_id}"
    assert (
        a_client.patch(
            url, json={"role": "council_admin"}, headers=csrf_headers(a_session)
        ).status_code
        == 403
    )
    assert a_client.delete(url, headers=csrf_headers(a_session)).status_code == 403


def test_membership_id_from_council_b_is_not_found_under_council_a(two_councils) -> None:
    """Using A's URL with B's membership ID must not reach B's row."""
    a_client, a_session = two_councils["clients"]["harare"]
    a_id = two_councils["harare"]["id"]
    officer_id = two_councils["b_officer"]["membership_id"]
    url = f"/api/v1/councils/{a_id}/members/{officer_id}"
    assert (
        a_client.patch(
            url, json={"role": "council_admin"}, headers=csrf_headers(a_session)
        ).status_code
        == 404
    )
    assert a_client.delete(url, headers=csrf_headers(a_session)).status_code == 404

    b_client, _ = two_councils["clients"]["bulawayo"]
    b_members = b_client.get(f"/api/v1/councils/{two_councils['bulawayo']['id']}/members").json()
    officer = next(m for m in b_members["items"] if m["membership_id"] == officer_id)
    assert officer["role"] == "maintenance_officer"


def test_member_lists_and_audit_logs_contain_only_own_council(two_councils) -> None:
    a_client, _ = two_councils["clients"]["harare"]
    a_id = two_councils["harare"]["id"]
    members = a_client.get(f"/api/v1/councils/{a_id}/members").json()
    assert [m["email"] for m in members["items"]] == ["admin@harare.example.com"]
    audit = a_client.get(f"/api/v1/councils/{a_id}/audit-logs").json()
    assert audit["total"] == 2  # council.created + first admin appointed
    assert "bulawayo" not in str(audit)


def test_client_cannot_supply_a_council_id_in_the_body(two_councils) -> None:
    a_client, a_session = two_councils["clients"]["harare"]
    response = a_client.post(
        f"/api/v1/councils/{two_councils['harare']['id']}/members",
        json={
            "email": "admin@harare.example.com",
            "role": "maintenance_officer",
            "council_id": two_councils["bulawayo"]["id"],
        },
        headers=csrf_headers(a_session),
    )
    assert response.status_code == 422


def test_user_in_two_councils_sees_each_with_its_own_role(
    two_councils, make_client: Callable[[], TestClient]
) -> None:
    a_client, a_session = two_councils["clients"]["harare"]
    b_client, b_session = two_councils["clients"]["bulawayo"]
    shared = make_client()
    register(shared, email="shared@example.com")
    add_member(
        a_client,
        a_session,
        two_councils["harare"]["id"],
        "shared@example.com",
        "department_manager",
    )
    add_member(
        b_client,
        b_session,
        two_councils["bulawayo"]["id"],
        "shared@example.com",
        "verification_officer",
    )
    roles = {
        slug: shared.get(f"/api/v1/councils/{two_councils[slug]['id']}/workspace").json()["role"]
        for slug in ("harare", "bulawayo")
    }
    assert roles == {"harare": "department_manager", "bulawayo": "verification_officer"}
