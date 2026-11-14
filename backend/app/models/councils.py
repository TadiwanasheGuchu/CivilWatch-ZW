"""Councils (tenants) and staff memberships."""

import uuid
from datetime import datetime
from enum import StrEnum

from geoalchemy2 import Geometry
from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    String,
    text,
)
from sqlalchemy.dialects.postgresql import CITEXT, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from app.models.identity import User


class CouncilRole(StrEnum):
    COUNCIL_ADMIN = "council_admin"
    DEPARTMENT_MANAGER = "department_manager"
    VERIFICATION_OFFICER = "verification_officer"
    MAINTENANCE_OFFICER = "maintenance_officer"


_ROLE_VALUES = ", ".join(f"'{role.value}'" for role in CouncilRole)


class Council(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "councils"

    slug: Mapped[str] = mapped_column(CITEXT, unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    is_active: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, server_default="true"
    )
    # Populated in Milestone 4 (council boundaries); used for report routing.
    boundary: Mapped[object | None] = mapped_column(
        Geometry(geometry_type="MULTIPOLYGON", srid=4326, spatial_index=False)
    )

    __table_args__ = (
        CheckConstraint(r"slug ~ '^[a-z0-9]+(-[a-z0-9]+)*$'", name="slug_format"),
        CheckConstraint("char_length(name) > 0", name="name_not_empty"),
        Index("ix_councils_boundary", "boundary", postgresql_using="gist"),
    )


class CouncilMembership(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """A user's staff role in one council. Revoked rows are kept for history."""

    __tablename__ = "council_memberships"

    council_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("councils.id", ondelete="RESTRICT"), nullable=False
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    role: Mapped[CouncilRole] = mapped_column(String(32), nullable=False)
    granted_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL")
    )
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    council: Mapped[Council] = relationship(lazy="joined")
    user: Mapped[User] = relationship(foreign_keys=[user_id], lazy="joined")

    __table_args__ = (
        CheckConstraint(f"role IN ({_ROLE_VALUES})", name="role_valid"),
        # At most one *active* membership per user per council.
        Index(
            "uq_council_memberships_active",
            "council_id",
            "user_id",
            unique=True,
            postgresql_where=text("revoked_at IS NULL"),
        ),
        Index("ix_council_memberships_user_id", "user_id"),
    )

    @property
    def is_active(self) -> bool:
        return self.revoked_at is None
