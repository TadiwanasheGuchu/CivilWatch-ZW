"""Creating and reading in-app notifications.

Notifications are added inside the transaction of the change that causes
them, so a status change and its notification commit (or fail) together.
Each row is also the outbox for future email/SMS/WhatsApp delivery.
"""

import uuid
from datetime import UTC, datetime

from sqlalchemy import func, select, update
from sqlalchemy.orm import Session

from app.core.errors import NotFoundError
from app.models.engagement import Notification, NotificationKind
from app.models.identity import User
from app.models.issues import Issue, IssueStatus, IssueStatusHistory

S = IssueStatus

STATUS_TITLES: dict[IssueStatus, str] = {
    S.UNDER_REVIEW: "Your report {ref} is being reviewed",
    S.NEEDS_INFORMATION: "The council needs more information about {ref}",
    S.VERIFIED: "Your report {ref} has been verified",
    S.ASSIGNED: "Your report {ref} has been assigned to a team",
    S.IN_PROGRESS: "Work has started on {ref}",
    S.RESOLVED: "{ref} has been resolved. Was it fixed?",
    S.REJECTED: "Your report {ref} was not accepted",
    S.DUPLICATE: "Your report {ref} was marked as a duplicate",
    S.CLOSED: "Your report {ref} is closed",
}


def _staff_link(issue: Issue) -> str:
    return f"/council/{issue.council_id}/reports/{issue.id}"


def _reporter_link(issue: Issue) -> str:
    return f"/reports/{issue.id}"


class Notifier:
    """Adds notifications to the current transaction. The caller commits."""

    def __init__(self, db: Session) -> None:
        self.db = db

    def _add(
        self,
        user_id: uuid.UUID,
        issue: Issue,
        kind: NotificationKind,
        title: str,
        link: str,
        body: str | None = None,
    ) -> None:
        self.db.add(
            Notification(
                user_id=user_id, issue_id=issue.id, kind=kind, title=title, body=body, link=link
            )
        )

    def status_changed(
        self, issue: Issue, to_status: IssueStatus, note: str | None, actor_id: uuid.UUID
    ) -> None:
        """Tell the reporter, unless they made the change themselves."""
        template = STATUS_TITLES.get(to_status)
        if template is None or issue.reporter_id == actor_id:
            return
        kind = (
            NotificationKind.INFORMATION_REQUESTED
            if to_status == S.NEEDS_INFORMATION
            else NotificationKind.STATUS_CHANGED
        )
        self._add(
            issue.reporter_id,
            issue,
            kind,
            template.format(ref=issue.reference),
            _reporter_link(issue),
            note,
        )

    def work_assigned(
        self, issue: Issue, assignee_id: uuid.UUID | None, actor_id: uuid.UUID
    ) -> None:
        if assignee_id is None or assignee_id == actor_id:
            return
        self._add(
            assignee_id,
            issue,
            NotificationKind.WORK_ASSIGNED,
            f"New work assigned to you: {issue.reference}",
            _staff_link(issue),
            issue.title,
        )

    def information_provided(self, issue: Issue, answer: str) -> None:
        """Tell the officer who asked for information that the reporter has answered."""
        asked_by = self._last_changed_by(issue, S.NEEDS_INFORMATION)
        if asked_by is None:
            return
        self._add(
            asked_by,
            issue,
            NotificationKind.INFORMATION_PROVIDED,
            f"The reporter answered your question on {issue.reference}",
            _staff_link(issue),
            answer,
        )

    def feedback_not_fixed(self, issue: Issue, comment: str | None) -> None:
        """Tell the officer who marked the report resolved that the reporter disagrees."""
        resolved_by = self._last_changed_by(issue, S.RESOLVED)
        if resolved_by is None:
            return
        self._add(
            resolved_by,
            issue,
            NotificationKind.FEEDBACK_NOT_FIXED,
            f"The reporter says {issue.reference} is not fixed",
            _staff_link(issue),
            comment,
        )

    def _last_changed_by(self, issue: Issue, status: IssueStatus) -> uuid.UUID | None:
        return self.db.scalar(
            select(IssueStatusHistory.changed_by_user_id)
            .where(IssueStatusHistory.issue_id == issue.id, IssueStatusHistory.to_status == status)
            .order_by(IssueStatusHistory.created_at.desc())
            .limit(1)
        )


class NotificationService:
    """Reading notifications. RLS also limits every query to the user's own rows."""

    def __init__(self, db: Session) -> None:
        self.db = db

    def list(
        self, user: User, *, unread_only: bool, offset: int, limit: int
    ) -> tuple[list[Notification], int]:
        base = select(Notification).where(Notification.user_id == user.id)
        if unread_only:
            base = base.where(Notification.read_at.is_(None))
        total = self.db.scalar(select(func.count()).select_from(base.subquery())) or 0
        items = self.db.scalars(
            base.order_by(Notification.created_at.desc(), Notification.id)
            .offset(offset)
            .limit(limit)
        ).all()
        return list(items), total

    def unread_count(self, user: User) -> int:
        return (
            self.db.scalar(
                select(func.count())
                .select_from(Notification)
                .where(Notification.user_id == user.id, Notification.read_at.is_(None))
            )
            or 0
        )

    def mark_read(self, user: User, notification_id: uuid.UUID) -> Notification:
        notification = self.db.scalar(
            select(Notification).where(
                Notification.id == notification_id, Notification.user_id == user.id
            )
        )
        if notification is None:
            raise NotFoundError("Notification not found.")
        if notification.read_at is None:
            notification.read_at = datetime.now(UTC)
            self.db.commit()
        return notification

    def mark_all_read(self, user: User) -> int:
        result = self.db.execute(
            update(Notification)
            .where(Notification.user_id == user.id, Notification.read_at.is_(None))
            .values(read_at=datetime.now(UTC))
        )
        self.db.commit()
        return result.rowcount or 0
