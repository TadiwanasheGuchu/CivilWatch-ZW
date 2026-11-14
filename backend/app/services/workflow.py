"""The report status workflow (CLAUDE.md section 8).

Every allowed status change is listed here, with the permission it needs,
whose reports it applies to, and whether a note to the reporter is
required. Anything not listed is refused. Assignment (VERIFIED -> ASSIGNED)
has its own endpoint because it also chooses a department.
"""

from dataclasses import dataclass
from enum import StrEnum
from typing import TYPE_CHECKING

from sqlalchemy import select

from app.models.councils import CouncilRole
from app.models.issues import IssueAssignment, IssueStatus
from app.permissions.council_access import CouncilAccess
from app.permissions.rbac import Permission

if TYPE_CHECKING:
    from sqlalchemy.orm import Session

    from app.models.issues import Issue

S = IssueStatus


class Scope(StrEnum):
    COUNCIL = "council"  # any staff member holding the permission
    DEPARTMENT = "department"  # administrators, or staff of the assigned department
    ASSIGNEE = "assignee"  # administrators, the department's manager, or the assigned officer


@dataclass(frozen=True)
class Transition:
    label: str
    permission: Permission
    scope: Scope = Scope.COUNCIL
    note_required: bool = False
    needs_duplicate_of: bool = False


TRANSITIONS: dict[tuple[IssueStatus, IssueStatus], Transition] = {
    (S.SUBMITTED, S.UNDER_REVIEW): Transition("Start review", Permission.ISSUES_REVIEW),
    (S.SUBMITTED, S.REJECTED): Transition("Reject", Permission.ISSUES_REVIEW, note_required=True),
    (S.SUBMITTED, S.DUPLICATE): Transition(
        "Mark as duplicate", Permission.ISSUES_REVIEW, needs_duplicate_of=True
    ),
    (S.UNDER_REVIEW, S.NEEDS_INFORMATION): Transition(
        "Ask the reporter for information", Permission.ISSUES_REVIEW, note_required=True
    ),
    (S.UNDER_REVIEW, S.VERIFIED): Transition("Verify", Permission.ISSUES_REVIEW),
    (S.UNDER_REVIEW, S.REJECTED): Transition(
        "Reject", Permission.ISSUES_REVIEW, note_required=True
    ),
    (S.UNDER_REVIEW, S.DUPLICATE): Transition(
        "Mark as duplicate", Permission.ISSUES_REVIEW, needs_duplicate_of=True
    ),
    # Staff may resume review themselves, e.g. when the reporter phoned in.
    (S.NEEDS_INFORMATION, S.UNDER_REVIEW): Transition("Resume review", Permission.ISSUES_REVIEW),
    (S.NEEDS_INFORMATION, S.REJECTED): Transition(
        "Reject", Permission.ISSUES_REVIEW, note_required=True
    ),
    (S.ASSIGNED, S.IN_PROGRESS): Transition(
        "Start work", Permission.ISSUES_WORK, scope=Scope.ASSIGNEE
    ),
    (S.IN_PROGRESS, S.RESOLVED): Transition(
        "Mark resolved", Permission.ISSUES_WORK, scope=Scope.ASSIGNEE, note_required=True
    ),
    (S.RESOLVED, S.CLOSED): Transition("Close", Permission.ISSUES_CLOSE, scope=Scope.DEPARTMENT),
    (S.RESOLVED, S.IN_PROGRESS): Transition(
        "Reopen", Permission.ISSUES_CLOSE, scope=Scope.DEPARTMENT, note_required=True
    ),
}

ASSIGNABLE_STATUSES = frozenset({S.VERIFIED, S.ASSIGNED, S.IN_PROGRESS})
# Repair evidence is added while the work is under way or just finished.
REPAIR_STATUSES = frozenset({S.IN_PROGRESS, S.RESOLVED})


def in_scope(access: CouncilAccess, scope: Scope, assignment: IssueAssignment | None) -> bool:
    if access.role == CouncilRole.COUNCIL_ADMIN or scope == Scope.COUNCIL:
        return True
    if assignment is None or access.membership is None:
        return False
    same_department = access.membership.department_id == assignment.department_id
    if scope == Scope.DEPARTMENT:
        return same_department
    if access.role == CouncilRole.DEPARTMENT_MANAGER:
        return same_department
    return assignment.assignee_user_id == access.user.id


def is_allowed(
    access: CouncilAccess, transition: Transition, assignment: IssueAssignment | None
) -> bool:
    return transition.permission in access.permissions and in_scope(
        access, transition.scope, assignment
    )


def available_transitions(
    access: CouncilAccess, status: IssueStatus, assignment: IssueAssignment | None
) -> list[tuple[IssueStatus, Transition]]:
    """The changes this caller may make now; the UI shows exactly these."""
    return [
        (to_status, transition)
        for (from_status, to_status), transition in TRANSITIONS.items()
        if from_status == status and is_allowed(access, transition, assignment)
    ]


def can_assign(access: CouncilAccess, status: IssueStatus) -> bool:
    return Permission.ISSUES_ASSIGN in access.permissions and status in ASSIGNABLE_STATUSES


def can_add_repair_photos(db: "Session", access: CouncilAccess, issue: "Issue") -> bool:
    """The staff doing the work: assignee, their department's manager, or an admin."""
    if Permission.ISSUES_WORK not in access.permissions or issue.status not in REPAIR_STATUSES:
        return False
    assignment = db.scalar(
        select(IssueAssignment).where(
            IssueAssignment.issue_id == issue.id, IssueAssignment.ended_at.is_(None)
        )
    )
    return in_scope(access, Scope.ASSIGNEE, assignment)
