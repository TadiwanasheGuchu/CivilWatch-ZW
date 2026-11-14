"""Council staff working on reports: review, assignment, progress, notes."""

import logging
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.errors import AppError, FieldValidationError, NotFoundError, PermissionDeniedError
from app.models.councils import CouncilMembership, CouncilRole
from app.models.departments import Department
from app.models.issues import (
    Issue,
    IssueAssignment,
    IssueStatus,
    IssueStatusHistory,
    IssueUpdate,
)
from app.permissions.council_access import CouncilAccess
from app.permissions.rbac import Permission
from app.repositories.operations import (
    CurrentAssignment,
    DepartmentRepository,
    OperationsRepository,
    QueueFilters,
)
from app.schemas.operations import AssignRequest, TransitionRequest
from app.schemas.pagination import PageParams
from app.services import workflow

logger = logging.getLogger(__name__)

WORKING_ROLES = frozenset({CouncilRole.DEPARTMENT_MANAGER, CouncilRole.MAINTENANCE_OFFICER})


class InvalidTransitionError(AppError):
    status_code = 409
    code = "invalid_transition"


@dataclass(frozen=True)
class StaffIssueView:
    issue: Issue
    assignment: CurrentAssignment | None
    reporter_name: str
    duplicate_of: Issue | None
    history: list[tuple[IssueStatusHistory, str | None]]
    updates: list[tuple[IssueUpdate, str | None]]
    transitions: list[tuple[IssueStatus, workflow.Transition]]
    can_assign: bool


class CouncilIssueService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.repo = OperationsRepository(db)
        self.departments = DepartmentRepository(db)

    # --- Reading ------------------------------------------------------------------------

    def summary(self, access: CouncilAccess) -> tuple[dict[IssueStatus, int], int]:
        access.require(Permission.ISSUES_VIEW)
        counts = self.repo.status_counts(access.council.id)
        return counts, self.repo.count_assigned_to(access.council.id, access.user.id)

    def queue(
        self, access: CouncilAccess, filters: QueueFilters, page: PageParams
    ) -> tuple[list[Issue], dict[uuid.UUID, CurrentAssignment], int]:
        access.require(Permission.ISSUES_VIEW)
        items, total = self.repo.list_queue(
            access.council.id, filters, offset=page.offset, limit=page.page_size
        )
        return items, self.repo.current_assignments([i.id for i in items]), total

    def detail(self, access: CouncilAccess, issue_id: uuid.UUID) -> StaffIssueView:
        access.require(Permission.ISSUES_VIEW)
        issue = self.repo.get_issue(access.council.id, issue_id)
        if issue is None:
            raise NotFoundError("Report not found.")
        assignment = self.repo.current_assignments([issue.id]).get(issue.id)
        current = assignment.assignment if assignment else None
        duplicate_of = (
            self.repo.get_issue(access.council.id, issue.duplicate_of_issue_id)
            if issue.duplicate_of_issue_id
            else None
        )
        return StaffIssueView(
            issue=issue,
            assignment=assignment,
            reporter_name=self.repo.reporter_name(issue.reporter_id),
            duplicate_of=duplicate_of,
            history=self.repo.history_with_names(issue.id),
            updates=self.repo.updates_with_names(issue.id),
            transitions=workflow.available_transitions(access, issue.status, current),
            can_assign=self._may_assign_now(access, issue.status, current),
        )

    # --- Changing status -----------------------------------------------------------------------

    def transition(
        self, access: CouncilAccess, issue_id: uuid.UUID, request: TransitionRequest
    ) -> None:
        access.require(Permission.ISSUES_VIEW)
        issue = self._lock(access, issue_id)
        current = self._current_assignment(issue)
        rule = workflow.TRANSITIONS.get((issue.status, request.to_status))
        if rule is None:
            raise InvalidTransitionError(
                f"A report that is {issue.status.replace('_', ' ').lower()} cannot be moved "
                f"to {request.to_status.replace('_', ' ').lower()}."
            )
        if not workflow.is_allowed(access, rule, current):
            raise PermissionDeniedError("You do not have permission to make this change.")
        if rule.note_required and not request.note:
            raise FieldValidationError("note", "Write a message for the reporter.")

        if rule.needs_duplicate_of:
            issue.duplicate_of_issue_id = self._duplicate_target(access, issue, request).id
        self._set_status(issue, request.to_status, access.user.id, request.note)
        self.db.commit()
        logger.info(
            "report status changed",
            extra={"issue_id": str(issue.id), "to_status": request.to_status.value},
        )

    def assign(self, access: CouncilAccess, issue_id: uuid.UUID, request: AssignRequest) -> None:
        access.require(Permission.ISSUES_ASSIGN)
        issue = self._lock(access, issue_id)
        if issue.status not in workflow.ASSIGNABLE_STATUSES:
            raise InvalidTransitionError("Only verified reports can be assigned.")
        department = self.departments.get(access.council.id, request.department_id)
        if department is None or not department.is_active:
            raise FieldValidationError("department_id", "Choose an active department.")
        if not self._may_assign_to(access, department):
            raise PermissionDeniedError("You can only assign reports within your own department.")
        if request.assignee_user_id is not None:
            self._check_assignee(access, department, request.assignee_user_id)

        now = datetime.now(UTC)
        previous = self._current_assignment(issue)
        if (
            previous is not None
            and access.role != CouncilRole.COUNCIL_ADMIN
            and previous.department_id != department.id
        ):
            raise PermissionDeniedError(
                "This report belongs to another department. Ask a council administrator."
            )
        if previous is not None:
            previous.ended_at = now
            self.db.flush()
        self.repo.add(
            IssueAssignment(
                issue_id=issue.id,
                council_id=access.council.id,
                department_id=department.id,
                assignee_user_id=request.assignee_user_id,
                assigned_by_user_id=access.user.id,
            )
        )
        if issue.status == IssueStatus.VERIFIED:
            note = request.note or f"Assigned to the {department.name} department."
            self._set_status(issue, IssueStatus.ASSIGNED, access.user.id, note)
        self.db.commit()
        logger.info("report assigned", extra={"issue_id": str(issue.id)})

    def add_update(self, access: CouncilAccess, issue_id: uuid.UUID, body: str) -> None:
        access.require(Permission.ISSUES_VIEW)
        issue = self.repo.get_issue(access.council.id, issue_id)
        if issue is None:
            raise NotFoundError("Report not found.")
        self.repo.add(
            IssueUpdate(
                issue_id=issue.id,
                council_id=access.council.id,
                author_user_id=access.user.id,
                body=body,
            )
        )
        self.db.commit()

    # --- Internals --------------------------------------------------------------------------------

    def _lock(self, access: CouncilAccess, issue_id: uuid.UUID) -> Issue:
        # Two officers acting at once: the second waits, then sees the new status.
        if not self.repo.lock_issue(access.council.id, issue_id):
            raise NotFoundError("Report not found.")
        issue = self.repo.get_issue(access.council.id, issue_id)
        assert issue is not None
        self.db.refresh(issue)
        return issue

    def _current_assignment(self, issue: Issue) -> IssueAssignment | None:
        found = self.repo.current_assignments([issue.id]).get(issue.id)
        return found.assignment if found else None

    def _set_status(
        self, issue: Issue, to_status: IssueStatus, actor_id: uuid.UUID, note: str | None
    ) -> None:
        self.repo.add(
            IssueStatusHistory(
                issue_id=issue.id,
                from_status=issue.status,
                to_status=to_status,
                changed_by_user_id=actor_id,
                note=note,
            )
        )
        issue.status = to_status

    def _duplicate_target(
        self, access: CouncilAccess, issue: Issue, request: TransitionRequest
    ) -> Issue:
        if not request.duplicate_of_reference:
            raise FieldValidationError(
                "duplicate_of_reference", "Give the reference of the original report."
            )
        number = int(request.duplicate_of_reference.removeprefix("CW-"))
        target = self.repo.find_by_reference(access.council.id, number)
        if target is None or target.id == issue.id:
            raise FieldValidationError(
                "duplicate_of_reference", "No other report in this council has that reference."
            )
        if target.status in (IssueStatus.DUPLICATE, IssueStatus.REJECTED):
            raise FieldValidationError(
                "duplicate_of_reference",
                "Point to the original report, not a rejected or duplicate one.",
            )
        return target

    def _may_assign_to(self, access: CouncilAccess, department: Department) -> bool:
        if access.role == CouncilRole.COUNCIL_ADMIN:
            return True
        return access.membership is not None and access.membership.department_id == department.id

    def _may_assign_now(
        self, access: CouncilAccess, status: IssueStatus, current: IssueAssignment | None
    ) -> bool:
        if not workflow.can_assign(access, status):
            return False
        if access.role == CouncilRole.COUNCIL_ADMIN:
            return True
        own_department = access.membership.department_id if access.membership else None
        if own_department is None:
            return False
        # Managers may assign new work to their department, or reassign within it.
        return current is None or current.department_id == own_department

    def _check_assignee(
        self, access: CouncilAccess, department: Department, user_id: uuid.UUID
    ) -> None:
        membership = self.db.scalar(
            select(CouncilMembership).where(
                CouncilMembership.council_id == access.council.id,
                CouncilMembership.user_id == user_id,
                CouncilMembership.revoked_at.is_(None),
            )
        )
        if (
            membership is None
            or membership.role not in WORKING_ROLES
            or membership.department_id != department.id
        ):
            raise FieldValidationError(
                "assignee_user_id",
                f"Choose a manager or maintenance officer of the {department.name} department.",
            )
