"""The reporter's answer to "Was the problem fixed?"."""

import uuid

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.errors import AppError, ConflictError, NotFoundError
from app.models.engagement import ResolutionFeedback
from app.models.identity import User
from app.models.issues import Issue, IssueStatus
from app.services.notifications import Notifier

FEEDBACK_STATUSES = frozenset({IssueStatus.RESOLVED, IssueStatus.CLOSED})


class FeedbackNotOpenError(AppError):
    status_code = 409
    code = "feedback_not_open"


class FeedbackService:
    def __init__(self, db: Session) -> None:
        self.db = db

    def for_issue(self, issue_id: uuid.UUID) -> ResolutionFeedback | None:
        return self.db.scalar(
            select(ResolutionFeedback).where(ResolutionFeedback.issue_id == issue_id)
        )

    def submit(
        self, reporter: User, issue_id: uuid.UUID, *, fixed: bool, comment: str | None
    ) -> ResolutionFeedback:
        issue = self.db.get(Issue, issue_id)
        if issue is None or issue.reporter_id != reporter.id:
            raise NotFoundError("Report not found.")
        if issue.status not in FEEDBACK_STATUSES:
            raise FeedbackNotOpenError(
                "You can say whether it was fixed once the council has resolved it."
            )
        if self.for_issue(issue.id) is not None:
            raise ConflictError("You have already told the council whether this was fixed.")
        feedback = ResolutionFeedback(
            issue_id=issue.id,
            council_id=issue.council_id,
            reporter_id=reporter.id,
            fixed=fixed,
            comment=comment,
        )
        self.db.add(feedback)
        if not fixed:
            # The council decides what happens next; nothing reopens automatically.
            Notifier(self.db).feedback_not_fixed(issue, comment)
        try:
            self.db.commit()
        except IntegrityError as exc:
            self.db.rollback()
            raise ConflictError(
                "You have already told the council whether this was fixed."
            ) from exc
        return feedback
