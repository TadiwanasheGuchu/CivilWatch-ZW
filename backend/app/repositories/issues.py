"""Data access for reports. RLS also restricts every query (see migration 0004)."""

import uuid

from sqlalchemy import Select, func, select
from sqlalchemy.orm import Session

from app.models.issues import (
    PUBLISHED_STATUSES,
    Issue,
    IssueCategory,
    IssueStatus,
    IssueStatusHistory,
    IssueVisibility,
)


def _page(
    db: Session, stmt: Select[tuple[Issue]], offset: int, limit: int
) -> tuple[list[Issue], int]:
    total = db.scalar(select(func.count()).select_from(stmt.order_by(None).subquery())) or 0
    items = db.scalars(stmt.order_by(Issue.created_at.desc(), Issue.id).offset(offset).limit(limit))
    return list(items.all()), total


class CategoryRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def list_active(self) -> list[IssueCategory]:
        stmt = select(IssueCategory).where(IssueCategory.is_active.is_(True))
        return list(self.db.scalars(stmt.order_by(IssueCategory.sort_order)).all())

    def get_active(self, category_id: uuid.UUID) -> IssueCategory | None:
        category = self.db.get(IssueCategory, category_id)
        return category if category and category.is_active else None


class IssueRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def add(self, issue: Issue) -> Issue:
        self.db.add(issue)
        self.db.flush()
        return issue

    def get(self, issue_id: uuid.UUID) -> Issue | None:
        return self.db.get(Issue, issue_id)

    def list_for_reporter(
        self, reporter_id: uuid.UUID, *, offset: int, limit: int
    ) -> tuple[list[Issue], int]:
        stmt = select(Issue).where(Issue.reporter_id == reporter_id)
        return _page(self.db, stmt, offset, limit)

    def list_published(
        self,
        *,
        council_id: uuid.UUID | None,
        category_code: str | None,
        status: IssueStatus | None,
        offset: int,
        limit: int,
    ) -> tuple[list[Issue], int]:
        # Explicit publication filter; RLS enforces the same rule underneath.
        stmt = select(Issue).where(
            Issue.visibility == IssueVisibility.PUBLIC,
            Issue.status.in_(PUBLISHED_STATUSES),
        )
        if council_id is not None:
            stmt = stmt.where(Issue.council_id == council_id)
        if category_code is not None:
            stmt = stmt.join(Issue.category).where(IssueCategory.code == category_code)
        if status is not None:
            stmt = stmt.where(Issue.status == status)
        return _page(self.db, stmt, offset, limit)

    def history(self, issue_id: uuid.UUID) -> list[IssueStatusHistory]:
        stmt = (
            select(IssueStatusHistory)
            .where(IssueStatusHistory.issue_id == issue_id)
            .order_by(IssueStatusHistory.created_at, IssueStatusHistory.id)
        )
        return list(self.db.scalars(stmt).all())

    def add_history(self, entry: IssueStatusHistory) -> None:
        self.db.add(entry)
