"""A council with departments and one member of staff per role, plus a resident's report."""

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from fastapi.testclient import TestClient

from app.models.councils import CouncilRole
from tests.conftest import add_member, csrf_headers, register, sign_in
from tests.issue_helpers import new_resident, report_payload, setup_councils, submit


@dataclass
class Actor:
    client: TestClient
    session: dict[str, Any]

    @property
    def id(self) -> str:
        return self.session["user"]["id"]

    def get(self, path: str):
        return self.client.get(path)

    def post(self, path: str, json: dict | None = None):
        return self.client.post(path, json=json, headers=csrf_headers(self.session))

    def patch(self, path: str, json: dict):
        return self.client.patch(path, json=json, headers=csrf_headers(self.session))


def build_council(make_client: Callable[[], TestClient]) -> dict[str, Any]:
    world = setup_councils(make_client)
    platform, platform_session = world["platform"], world["platform_session"]
    council_id = world["harare"]["id"]

    def staff(email: str, role: CouncilRole) -> Actor:
        client = make_client()
        register(client, email=email, full_name=email.split("@")[0].replace(".", " ").title())
        add_member(platform, platform_session, council_id, email, role)
        return Actor(client, sign_in(client, email))

    admin = staff("admin@harare.example.com", CouncilRole.COUNCIL_ADMIN)
    base = f"/api/v1/councils/{council_id}"
    roads = admin.post(
        f"{base}/departments", {"name": "Roads", "description": "Roads and bridges"}
    ).json()
    water = admin.post(f"{base}/departments", {"name": "Water and Sewerage"}).json()

    verifier = staff("verifier@harare.example.com", CouncilRole.VERIFICATION_OFFICER)
    roads_manager = staff("roads.manager@harare.example.com", CouncilRole.DEPARTMENT_MANAGER)
    water_manager = staff("water.manager@harare.example.com", CouncilRole.DEPARTMENT_MANAGER)
    roads_officer = staff("roads.officer@harare.example.com", CouncilRole.MAINTENANCE_OFFICER)
    roads_officer_2 = staff("roads.officer2@harare.example.com", CouncilRole.MAINTENANCE_OFFICER)
    water_officer = staff("water.officer@harare.example.com", CouncilRole.MAINTENANCE_OFFICER)

    members = {m["user_id"]: m for m in admin.get(f"{base}/members?page_size=100").json()["items"]}
    for actor, department in (
        (roads_manager, roads),
        (roads_officer, roads),
        (roads_officer_2, roads),
        (water_manager, water),
        (water_officer, water),
    ):
        membership_id = members[actor.id]["membership_id"]
        response = admin.patch(
            f"{base}/members/{membership_id}", {"department_id": department["id"]}
        )
        assert response.status_code == 200, response.text

    resident_client, resident_session = new_resident(make_client, "resident@example.com")
    resident = Actor(resident_client, resident_session)
    issue = submit(
        resident_client, resident_session, report_payload(world, visibility="PRIVATE")
    ).json()
    return {
        **world,
        "base": base,
        "council_id": council_id,
        "roads": roads,
        "water": water,
        "admin": admin,
        "verifier": verifier,
        "roads_manager": roads_manager,
        "water_manager": water_manager,
        "roads_officer": roads_officer,
        "roads_officer_2": roads_officer_2,
        "water_officer": water_officer,
        "resident": resident,
        "issue": issue,
        "issue_url": f"{base}/issues/{issue['id']}",
    }


def move(actor: Actor, issue_url: str, to_status: str, **extra: Any):
    return actor.post(f"{issue_url}/transitions", {"to_status": to_status, **extra})


def verify(c: dict[str, Any]) -> None:
    assert move(c["verifier"], c["issue_url"], "UNDER_REVIEW").status_code == 200
    assert move(c["verifier"], c["issue_url"], "VERIFIED").status_code == 200


def assign_to_roads_officer(c: dict[str, Any]) -> None:
    verify(c)
    response = c["roads_manager"].post(
        f"{c['issue_url']}/assignment",
        {"department_id": c["roads"]["id"], "assignee_user_id": c["roads_officer"].id},
    )
    assert response.status_code == 200, response.text
