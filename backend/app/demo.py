"""Seed a demonstration environment with clearly labelled SAMPLE data.

Everything goes through the same services, permission checks and workflow
rules the API uses, acting as each person in turn (with RLS bound to them),
so the history, notifications and audit log look exactly as real use would
leave them. Every report title starts with "Sample:", every account uses an
example.com address, and the councils get SAMPLE boundaries.

Passwords are generated at random and printed once; nothing is hardcoded.
"""

import secrets
import uuid
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from typing import TypeVar

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.cli import load_sample_boundaries
from app.core.config import get_settings
from app.core.database import bind_rls_user, get_session_factory
from app.core.security import hash_password
from app.models.councils import Council, CouncilRole
from app.models.identity import User
from app.models.issues import IssueCategory, IssueStatus, IssueVisibility
from app.permissions.council_access import resolve_council_access
from app.schemas.issues import CreateIssueRequest
from app.schemas.operations import AssignRequest, CreateDepartmentRequest, TransitionRequest
from app.services.audit import record_audit
from app.services.councils import CouncilService
from app.services.departments import DepartmentService
from app.services.feedback import FeedbackService
from app.services.issues import IssueService
from app.services.operations import CouncilIssueService

T = TypeVar("T")
S = IssueStatus
SAMPLE_PREFIX = "Sample: "
MARKER_EMAIL = "demo.platform@example.com"
DEPARTMENTS = ("Roads", "Water and Sewerage", "Waste Management", "Public Lighting")

# (title, category, department, visibility, final status, offset north km, offset east km)
REPORTS: dict[str, list[tuple[str, str, str, str, S, float, float]]] = {
    "harare": [
        ("Deep pothole on the inner lane", "roads", "Roads", "PUBLIC", S.RESOLVED, 0.6, 0.4),
        (
            "Streetlights out along the avenue",
            "streetlights",
            "Public Lighting",
            "PUBLIC",
            S.IN_PROGRESS,
            -0.8,
            0.9,
        ),
        (
            "Burst water main flooding the pavement",
            "water",
            "Water and Sewerage",
            "PUBLIC",
            S.ASSIGNED,
            1.2,
            -0.7,
        ),
        (
            "Uncollected refuse at the market",
            "waste",
            "Waste Management",
            "PUBLIC",
            S.VERIFIED,
            -1.4,
            -1.1,
        ),
        (
            "Blocked storm drain near the clinic",
            "drainage",
            "Water and Sewerage",
            "PUBLIC",
            S.CLOSED,
            2.0,
            1.5,
        ),
        (
            "Damaged footbridge railing",
            "bridges-pavements",
            "Roads",
            "PUBLIC",
            S.UNDER_REVIEW,
            -2.1,
            0.3,
        ),
        (
            "Leaking pipe behind my house",
            "water",
            "Water and Sewerage",
            "PRIVATE",
            S.IN_PROGRESS,
            0.2,
            -1.9,
        ),
        ("Pothole reported twice by mistake", "roads", "Roads", "PUBLIC", S.REJECTED, 0.9, 2.2),
        (
            "Broken streetlight outside the school",
            "streetlights",
            "Public Lighting",
            "PUBLIC",
            S.SUBMITTED,
            -0.4,
            -0.3,
        ),
    ],
    "bulawayo": [
        ("Cracked road surface at the junction", "roads", "Roads", "PUBLIC", S.RESOLVED, 0.5, -0.6),
        (
            "Overflowing sewer manhole",
            "water",
            "Water and Sewerage",
            "PUBLIC",
            S.IN_PROGRESS,
            -0.9,
            0.7,
        ),
        (
            "Illegal dumping beside the park",
            "waste",
            "Waste Management",
            "PUBLIC",
            S.VERIFIED,
            1.3,
            1.0,
        ),
        (
            "Flooded underpass after rain",
            "drainage",
            "Water and Sewerage",
            "PRIVATE",
            S.SUBMITTED,
            -1.5,
            -1.2,
        ),
    ],
}

# The path from SUBMITTED to each final status, as staff would take it.
PATHS: dict[S, list[S]] = {
    S.SUBMITTED: [],
    S.UNDER_REVIEW: [S.UNDER_REVIEW],
    S.REJECTED: [S.UNDER_REVIEW, S.REJECTED],
    S.VERIFIED: [S.UNDER_REVIEW, S.VERIFIED],
    S.ASSIGNED: [S.UNDER_REVIEW, S.VERIFIED, S.ASSIGNED],
    S.IN_PROGRESS: [S.UNDER_REVIEW, S.VERIFIED, S.ASSIGNED, S.IN_PROGRESS],
    S.RESOLVED: [S.UNDER_REVIEW, S.VERIFIED, S.ASSIGNED, S.IN_PROGRESS, S.RESOLVED],
    S.CLOSED: [S.UNDER_REVIEW, S.VERIFIED, S.ASSIGNED, S.IN_PROGRESS, S.RESOLVED, S.CLOSED],
}
NOTES = {
    S.REJECTED: "This duplicates another sample report at the same spot.",
    S.RESOLVED: "Repaired by the sample works team.",
    S.CLOSED: "Closed after the reporter confirmed the repair.",
}


@dataclass
class Account:
    email: str
    full_name: str
    password: str
    id: uuid.UUID | None = None


@dataclass
class CouncilCrew:
    council_id: uuid.UUID
    admin: Account
    verifier: Account
    manager: Account
    officer: Account
    departments: dict[str, uuid.UUID]


class DemoSeeder:
    def __init__(
        self,
        session_factory: Callable[[], Session] | None = None,
        *,
        shared_password: str | None = None,
    ) -> None:
        """`shared_password`, if given, is used for every sample account except the
        platform administrator, which always gets a random password nobody is shown."""
        self.session_factory = session_factory or get_session_factory()
        self.shared_password = shared_password
        self.settings = get_settings()
        self.accounts: list[Account] = []

    @contextmanager
    def acting_as(self, account: Account | None) -> Iterator[Session]:
        with self.session_factory() as db:
            if account is not None and account.id is not None:
                bind_rls_user(db, account.id)
            yield db

    def _user(self, db: Session, account: Account) -> User:
        user = db.get(User, account.id)
        assert user is not None
        return user

    def already_seeded(self) -> bool:
        with self.acting_as(None) as db:
            return db.scalar(select(func.count()).where(User.email == MARKER_EMAIL)) > 0

    def create_account(
        self, email: str, full_name: str, *, platform_admin: bool = False
    ) -> Account:
        password = (
            self.shared_password
            if self.shared_password and not platform_admin
            else secrets.token_urlsafe(16)
        )
        account = Account(email, full_name, password)
        with self.acting_as(None) as db:
            user = User(
                email=email,
                full_name=full_name,
                password_hash=hash_password(account.password),
                is_platform_admin=platform_admin,
            )
            db.add(user)
            db.flush()
            if platform_admin:
                record_audit(
                    db,
                    action="platform_admin.granted",
                    actor_user_id=None,
                    target_type="user",
                    target_id=user.id,
                    details={"via": "cli-demo"},
                )
            db.commit()
            account.id = user.id
        self.accounts.append(account)
        return account

    def _council_call(self, account: Account, council_id: uuid.UUID, fn: Callable[..., T]) -> T:
        with self.acting_as(account) as db:
            access = resolve_council_access(db, self._user(db, account), council_id)
            return fn(db, access)

    def build_crew(self, platform: Account, slug: str, city: str) -> CouncilCrew:
        with self.acting_as(None) as db:
            council_id = db.scalar(select(Council.id).where(Council.slug == slug))
        assert council_id is not None, slug
        prefix = f"demo.{slug}"
        admin = self.create_account(f"{prefix}.admin@example.com", f"{city} Sample Administrator")
        verifier = self.create_account(f"{prefix}.verifier@example.com", f"{city} Sample Verifier")
        manager = self.create_account(
            f"{prefix}.roads.manager@example.com", f"{city} Sample Roads Manager"
        )
        officer = self.create_account(
            f"{prefix}.officer@example.com", f"{city} Sample Works Officer"
        )

        self._council_call(
            platform,
            council_id,
            lambda db, access: CouncilService(db).add_member(
                access, email=admin.email, role=CouncilRole.COUNCIL_ADMIN
            ),
        )
        departments = {
            name: self._council_call(
                admin,
                council_id,
                lambda db, access, name=name: (
                    DepartmentService(db).create(access, CreateDepartmentRequest(name=name)).id
                ),
            )
            for name in DEPARTMENTS
        }
        for account, role in (
            (verifier, CouncilRole.VERIFICATION_OFFICER),
            (manager, CouncilRole.DEPARTMENT_MANAGER),
            (officer, CouncilRole.MAINTENANCE_OFFICER),
        ):
            membership = self._council_call(
                admin,
                council_id,
                lambda db, access, account=account, role=role: CouncilService(db).add_member(
                    access, email=account.email, role=role
                ),
            )
            if role != CouncilRole.VERIFICATION_OFFICER:
                self._council_call(
                    admin,
                    council_id,
                    lambda db, access, mid=membership.id: CouncilService(db).update_member(
                        access, mid, department_id=departments["Roads"], department_given=True
                    ),
                )
        return CouncilCrew(council_id, admin, verifier, manager, officer, departments)

    def _centre(self, council_id: uuid.UUID) -> tuple[float, float]:
        with self.acting_as(None) as db:
            point = func.ST_PointOnSurface(Council.boundary)
            lat, lon = db.execute(
                select(func.ST_Y(point), func.ST_X(point)).where(Council.id == council_id)
            ).one()
        return float(lat), float(lon)

    def seed_reports(self, crew: CouncilCrew, slug: str, residents: list[Account]) -> int:
        lat0, lon0 = self._centre(crew.council_id)
        with self.acting_as(None) as db:
            categories = dict(db.execute(select(IssueCategory.code, IssueCategory.id)).all())
        count = 0
        for index, (title, category, department, visibility, final, north, east) in enumerate(
            REPORTS[slug]
        ):
            reporter = residents[index % len(residents)]
            with self.acting_as(reporter) as db:
                issue = IssueService(db, self.settings).submit(
                    self._user(db, reporter),
                    CreateIssueRequest(
                        council_id=crew.council_id,
                        category_id=categories[category],
                        title=SAMPLE_PREFIX + title,
                        description=(
                            "Sample report created for the CivicWatch ZW demonstration. "
                            "It does not describe a real problem."
                        ),
                        latitude=lat0 + north / 111.0,
                        longitude=lon0 + east / 105.0,
                        location_description="Sample location",
                        visibility=IssueVisibility(visibility),
                    ),
                )
                issue_id = issue.id
            count += 1
            for step in PATHS[final]:
                self._advance(crew, issue_id, step, department)
            if final in (S.RESOLVED, S.CLOSED):
                with self.acting_as(reporter) as db:
                    FeedbackService(db).submit(
                        self._user(db, reporter),
                        issue_id,
                        fixed=final == S.CLOSED or index % 2 == 0,
                        comment="Sample feedback.",
                    )
        return count

    def _advance(self, crew: CouncilCrew, issue_id: uuid.UUID, step: S, department: str) -> None:
        if step == S.ASSIGNED:
            # Roads work goes to the sample officer; other departments have no
            # officers yet, so their reports stay with the department.
            assignee = crew.officer.id if department == "Roads" else None
            self._council_call(
                crew.admin,
                crew.council_id,
                lambda db, access: CouncilIssueService(db).assign(
                    access,
                    issue_id,
                    AssignRequest(
                        department_id=crew.departments[department], assignee_user_id=assignee
                    ),
                ),
            )
            return
        actor = crew.verifier if step in (S.UNDER_REVIEW, S.VERIFIED, S.REJECTED) else crew.admin
        if step in (S.IN_PROGRESS, S.RESOLVED) and department == "Roads":
            actor = crew.officer
        self._council_call(
            actor,
            crew.council_id,
            lambda db, access: CouncilIssueService(db).transition(
                access, issue_id, TransitionRequest(to_status=step, note=NOTES.get(step))
            ),
        )

    def run(self) -> list[Account]:
        if self.already_seeded():
            raise SystemExit("Demo data is already present; nothing was changed.")
        for line in load_sample_boundaries(create_missing=True):
            print(line)
        platform = self.create_account(
            MARKER_EMAIL, "Sample Platform Administrator", platform_admin=True
        )
        residents = [
            self.create_account(f"demo.resident{n}@example.com", f"Sample Resident {n}")
            for n in (1, 2, 3)
        ]
        total = 0
        for slug, city in (("harare", "Harare"), ("bulawayo", "Bulawayo")):
            crew = self.build_crew(platform, slug, city)
            total += self.seed_reports(crew, slug, residents)
        print(f"Created {total} sample reports.")
        return self.accounts
