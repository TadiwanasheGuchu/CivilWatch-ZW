"""Notifications and residents' feedback on resolved reports."""

import uuid
from datetime import UTC, datetime
from enum import StrEnum

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, UUIDPrimaryKeyMixin


class NotificationKind(StrEnum):
    STATUS_CHANGED = "status_changed"
    INFORMATION_REQUESTED = "information_requested"
    INFORMATION_PROVIDED = "information_provided"
    WORK_ASSIGNED = "work_assigned"
    FEEDBACK_NOT_FIXED = "feedback_not_fixed"


_KINDS = ", ".join(f"'{k.value}'" for k in NotificationKind)


class Notification(UUIDPrimaryKeyMixin, Base):
    """An in-app message to one person. Also the outbox for future email/SMS delivery."""

    __tablename__ = "notifications"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    issue_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("issues.id", ondelete="CASCADE")
    )
    kind: Mapped[NotificationKind] = mapped_column(String(32), nullable=False)
    title: Mapped[str] = mapped_column(String(160), nullable=False)
    body: Mapped[str | None] = mapped_column(Text)
    # Relative link inside the app, e.g. /reports/<id>.
    link: Mapped[str] = mapped_column(String(255), nullable=False)
    # Set in Python so inserts need no RETURNING (the recipient is usually
    # someone else, whose rows the actor may not read).
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
        server_default=func.now(),
    )
    read_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    # Email delivery (outbox), handled by the worker under its own database role.
    email_sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    email_attempts: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default="0"
    )
    email_last_error: Mapped[str | None] = mapped_column(String(300))

    __table_args__ = (
        CheckConstraint(f"kind IN ({_KINDS})", name="kind_valid"),
        CheckConstraint("link LIKE '/%' AND link NOT LIKE '//%'", name="link_relative"),
        Index("ix_notifications_user_id_created_at", "user_id", "created_at"),
        Index(
            "ix_notifications_unread",
            "user_id",
            postgresql_where=text("read_at IS NULL"),
        ),
        Index(
            "ix_notifications_email_pending",
            "created_at",
            postgresql_where=text("email_sent_at IS NULL"),
        ),
    )


class ResolutionFeedback(UUIDPrimaryKeyMixin, Base):
    """The reporter's answer to "Was the problem fixed?" — once per report."""

    __tablename__ = "resolution_feedback"

    issue_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("issues.id", ondelete="RESTRICT"),
        unique=True,
        nullable=False,
    )
    council_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("councils.id", ondelete="RESTRICT"), nullable=False
    )
    reporter_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    fixed: Mapped[bool] = mapped_column(Boolean, nullable=False)
    # Shown to the reporter and council staff only, never publicly.
    comment: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
        server_default=func.now(),
    )

    __table_args__ = (
        CheckConstraint("comment IS NULL OR char_length(comment) <= 1000", name="comment_length"),
        Index("ix_resolution_feedback_council_id", "council_id"),
    )
