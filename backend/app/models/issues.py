"""Infrastructure reports ("issues"), their categories and status history."""

import uuid
from datetime import UTC, datetime
from enum import StrEnum

from geoalchemy2 import Geography, Geometry
from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Identity,
    Index,
    Integer,
    String,
    Text,
    cast,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import CITEXT, UUID
from sqlalchemy.orm import Mapped, column_property, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from app.models.councils import Council


class IssueStatus(StrEnum):
    SUBMITTED = "SUBMITTED"
    UNDER_REVIEW = "UNDER_REVIEW"
    NEEDS_INFORMATION = "NEEDS_INFORMATION"
    VERIFIED = "VERIFIED"
    ASSIGNED = "ASSIGNED"
    IN_PROGRESS = "IN_PROGRESS"
    RESOLVED = "RESOLVED"
    REJECTED = "REJECTED"
    DUPLICATE = "DUPLICATE"
    CLOSED = "CLOSED"


class IssueVisibility(StrEnum):
    PUBLIC = "PUBLIC"
    PRIVATE = "PRIVATE"


# A PUBLIC report is shown to everyone only once a council has verified it
# (product decision, docs/01-product-requirements.md). Rejected and
# duplicate reports are never published.
PUBLISHED_STATUSES = frozenset(
    {
        IssueStatus.VERIFIED,
        IssueStatus.ASSIGNED,
        IssueStatus.IN_PROGRESS,
        IssueStatus.RESOLVED,
        IssueStatus.CLOSED,
    }
)

_STATUS_VALUES = ", ".join(f"'{s.value}'" for s in IssueStatus)
_PUBLISHED_VALUES = ", ".join(f"'{s.value}'" for s in sorted(PUBLISHED_STATUSES))


class IssueCategory(UUIDPrimaryKeyMixin, Base):
    """Platform-wide reference data, seeded by migration."""

    __tablename__ = "issue_categories"

    code: Mapped[str] = mapped_column(CITEXT, unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(80), nullable=False)
    description: Mapped[str] = mapped_column(String(240), nullable=False)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False)
    is_active: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, server_default="true"
    )


class Issue(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "issues"

    # Short, sequential number residents can quote, shown as CW-000123.
    reference_number: Mapped[int] = mapped_column(
        BigInteger, Identity(always=True), unique=True, nullable=False
    )
    council_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("councils.id", ondelete="RESTRICT"), nullable=False
    )
    reporter_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    category_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("issue_categories.id", ondelete="RESTRICT"), nullable=False
    )
    title: Mapped[str] = mapped_column(String(120), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[IssueStatus] = mapped_column(
        String(32), nullable=False, default=IssueStatus.SUBMITTED
    )
    visibility: Mapped[IssueVisibility] = mapped_column(String(16), nullable=False)
    location: Mapped[object] = mapped_column(
        Geography(geometry_type="POINT", srid=4326, spatial_index=False), nullable=False
    )
    location_description: Mapped[str | None] = mapped_column(String(200))

    latitude: Mapped[float] = column_property(func.ST_Y(cast(location, Geometry)))
    longitude: Mapped[float] = column_property(func.ST_X(cast(location, Geometry)))

    council: Mapped[Council] = relationship(lazy="joined")
    category: Mapped[IssueCategory] = relationship(lazy="joined")
    # selectin: one extra query for a whole page of reports, never N+1.
    photos: Mapped[list["IssueMedia"]] = relationship(
        lazy="selectin", order_by="IssueMedia.created_at", viewonly=True
    )

    __table_args__ = (
        CheckConstraint(f"status IN ({_STATUS_VALUES})", name="status_valid"),
        CheckConstraint("visibility IN ('PUBLIC', 'PRIVATE')", name="visibility_valid"),
        CheckConstraint("char_length(title) BETWEEN 5 AND 120", name="title_length"),
        CheckConstraint("char_length(description) BETWEEN 10 AND 2000", name="description_length"),
        Index("ix_issues_location", "location", postgresql_using="gist"),
        Index("ix_issues_council_id_status", "council_id", "status"),
        Index("ix_issues_reporter_id_created_at", "reporter_id", "created_at"),
        # Public browsing only ever reads published public reports.
        Index(
            "ix_issues_published_created_at",
            "created_at",
            postgresql_where=text(f"visibility = 'PUBLIC' AND status IN ({_PUBLISHED_VALUES})"),
        ),
    )

    @property
    def reference(self) -> str:
        return f"CW-{self.reference_number:06d}"

    @property
    def is_published(self) -> bool:
        return self.visibility == IssueVisibility.PUBLIC and self.status in PUBLISHED_STATUSES


class IssueStatusHistory(UUIDPrimaryKeyMixin, Base):
    """One row per status change, never updated or deleted."""

    __tablename__ = "issue_status_history"

    issue_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("issues.id", ondelete="RESTRICT"), nullable=False
    )
    from_status: Mapped[IssueStatus | None] = mapped_column(String(32))
    to_status: Mapped[IssueStatus] = mapped_column(String(32), nullable=False)
    changed_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL")
    )
    # Set in Python so the INSERT needs no RETURNING (see AuditLog).
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
        server_default=func.now(),
    )

    __table_args__ = (
        CheckConstraint(f"to_status IN ({_STATUS_VALUES})", name="to_status_valid"),
        Index("ix_issue_status_history_issue_id_created_at", "issue_id", "created_at"),
    )


class IssueMedia(UUIDPrimaryKeyMixin, Base):
    """A sanitised photo stored privately in object storage.

    Only object keys are stored; URLs are generated per request and expire.
    """

    __tablename__ = "issue_media"

    issue_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("issues.id", ondelete="RESTRICT"), nullable=False
    )
    uploaded_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL")
    )
    display_key: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    thumbnail_key: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    content_type: Mapped[str] = mapped_column(String(32), nullable=False)
    width: Mapped[int] = mapped_column(Integer, nullable=False)
    height: Mapped[int] = mapped_column(Integer, nullable=False)
    byte_size: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
        server_default=func.now(),
    )

    __table_args__ = (
        CheckConstraint("content_type = 'image/jpeg'", name="content_type_valid"),
        CheckConstraint("width > 0 AND height > 0 AND byte_size > 0", name="dimensions_positive"),
        Index("ix_issue_media_issue_id_created_at", "issue_id", "created_at"),
    )
