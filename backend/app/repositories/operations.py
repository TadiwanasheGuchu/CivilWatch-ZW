"""Data access for council-side work on reports.

Every query names the council explicitly; RLS restricts the same rows again.
"""

import uuid
from dataclasses import dataclass

from sqlalchemy import Select, func, or_, select
from sqlalchemy.orm import Session, aliased

from app.models.departments import Department
from app.models.identity import User
from app.models.issues import (
    Issue,
    IssueAssignment,
    IssueCategory,
    IssueStatus,
    IssueStatusHistory,
    IssueUpdate,
)


@dataclass(frozen=True)
class CurrentAssignment:
    assignment: IssueAssignment
    department_name: str
    assignee_name: str | None


@dataclass(frozen=True)
class QueueFilters:
    statuses: tuple[IssueStatus, ...] = ()
    category_code: str | None = None
    department_id: uuid.UUID | None = None
    assignee_user_id: uuid.UUID | None = None
    search: str | None = None
    oldest_first: bool = False


class DepartmentRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def list(self, council_id: uuid.UUID) -> list[Department]:
        stmt = select(Department).where(Department.council_id == council_id)
        return list(self.db.scalars(stmt.order_by(Department.name)).all())

    def get(self, council_id: uuid.UUID, department_id: uuid.UUID) -> Department | None:
        return self.db.scalar(
            select(Department).where(
                Department.council_id == council_id, Department.id == department_id
            )
        )

    def name_taken(
        self, council_id: uuid.UUID, name: str, exclude_id: uuid.UUID | None = None
    ) -> bool:
        stmt = select(Department.id).where(
            Department.council_id == council_id, Department.name == name
        )
        if exclude_id is not None:
            stmt = stmt.where(Department.id != exclude_id)
        return self.db.scalar(stmt) is not None

    def add(self, department: Department) -> Department:
        self.db.add(department)
        self.db.flush()
        return department


class OperationsRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    # --- Reports -----------------------------------------------------------------------

    def get_issue(self, council_id: uuid.UUID, issue_id: uuid.UUID) -> Issue | None:
        return self.db.scalar(
            select(Issue).where(Issue.council_id == council_id, Issue.id == issue_id)
        )

    def lock_issue(self, council_id: uuid.UUID, issue_id: uuid.UUID) -> bool:
        """Row-lock the report for the rest of the transaction. False if not found."""
        locked = self.db.scalar(
            select(Issue.id)
            .where(Issue.council_id == council_id, Issue.id == issue_id)
            .with_for_update()
        )
        return locked is not None

    def find_by_reference(self, council_id: uuid.UUID, reference_number: int) -> Issue | None:
        return self.db.scalar(
            select(Issue).where(
                Issue.council_id == council_id, Issue.reference_number == reference_number
            )
        )

    def _queue(self, council_id: uuid.UUID, filters: QueueFilters) -> Select[tuple[Issue]]:
        stmt = select(Issue).where(Issue.council_id == council_id)
        if filters.statuses:
            stmt = stmt.where(Issue.status.in_(filters.statuses))
        if filters.category_code:
            stmt = stmt.join(IssueCategory, IssueCategory.id == Issue.category_id).where(
                IssueCategory.code == filters.category_code
            )
        if filters.department_id or filters.assignee_user_id:
            current = aliased(IssueAssignment)
            stmt = stmt.join(current, (current.issue_id == Issue.id) & current.ended_at.is_(None))
            if filters.department_id:
                stmt = stmt.where(current.department_id == filters.department_id)
            if filters.assignee_user_id:
                stmt = stmt.where(current.assignee_user_id == filters.assignee_user_id)
        if filters.search:
            term = filters.search.strip()
            digits = term.upper().removeprefix("CW-").lstrip("0")
            clauses = [Issue.title.ilike(f"%{_escape_like(term)}%", escape="\\")]
            if digits.isdigit():
                clauses.append(Issue.reference_number == int(digits))
            stmt = stmt.where(or_(*clauses))
        return stmt

    def list_queue(
        self, council_id: uuid.UUID, filters: QueueFilters, *, offset: int, limit: int
    ) -> tuple[list[Issue], int]:
        stmt = self._queue(council_id, filters)
        total = self.db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
        order = Issue.created_at.asc() if filters.oldest_first else Issue.created_at.desc()
        items = self.db.scalars(stmt.order_by(order, Issue.id).offset(offset).limit(limit))
        return list(items.all()), total

    def status_counts(self, council_id: uuid.UUID) -> dict[IssueStatus, int]:
        rows = self.db.execute(
            select(Issue.status, func.count())
            .where(Issue.council_id == council_id)
            .group_by(Issue.status)
        ).all()
        return {IssueStatus(status): count for status, count in rows}

    def count_assigned_to(self, council_id: uuid.UUID, user_id: uuid.UUID) -> int:
        return (
            self.db.scalar(
                select(func.count())
                .select_from(IssueAssignment)
                .join(Issue, Issue.id == IssueAssignment.issue_id)
                .where(
                    IssueAssignment.council_id == council_id,
                    IssueAssignment.assignee_user_id == user_id,
                    IssueAssignment.ended_at.is_(None),
                    Issue.status.in_((IssueStatus.ASSIGNED, IssueStatus.IN_PROGRESS)),
                )
            )
            or 0
        )

    # --- Assignments ------------------------------------------------------------------------

    def current_assignments(self, issue_ids: list[uuid.UUID]) -> dict[uuid.UUID, CurrentAssignment]:
        """Current assignment per report, with names, in one query."""
        if not issue_ids:
            return {}
        assignee = aliased(User)
        rows = self.db.execute(
            select(IssueAssignment, Department.name, assignee.full_name)
            .join(Department, Department.id == IssueAssignment.department_id)
            .outerjoin(assignee, assignee.id == IssueAssignment.assignee_user_id)
            .where(IssueAssignment.issue_id.in_(issue_ids), IssueAssignment.ended_at.is_(None))
        ).all()
        return {row[0].issue_id: CurrentAssignment(row[0], row[1], row[2]) for row in rows}

    def add(self, entity: object) -> None:
        self.db.add(entity)

    # --- History and notes --------------------------------------------------------------------

    def history_with_names(
        self, issue_id: uuid.UUID
    ) -> list[tuple[IssueStatusHistory, str | None]]:
        rows = self.db.execute(
            select(IssueStatusHistory, User.full_name)
            .outerjoin(User, User.id == IssueStatusHistory.changed_by_user_id)
            .where(IssueStatusHistory.issue_id == issue_id)
            .order_by(IssueStatusHistory.created_at, IssueStatusHistory.id)
        ).all()
        return [(row[0], row[1]) for row in rows]

    def updates_with_names(self, issue_id: uuid.UUID) -> list[tuple[IssueUpdate, str | None]]:
        rows = self.db.execute(
            select(IssueUpdate, User.full_name)
            .outerjoin(User, User.id == IssueUpdate.author_user_id)
            .where(IssueUpdate.issue_id == issue_id)
            .order_by(IssueUpdate.created_at, IssueUpdate.id)
        ).all()
        return [(row[0], row[1]) for row in rows]

    def reporter_name(self, reporter_id: uuid.UUID) -> str:
        return self.db.scalar(select(User.full_name).where(User.id == reporter_id)) or "Unknown"


def _escape_like(term: str) -> str:
    """Treat %, _ and backslash in a search term literally."""
    return term.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
