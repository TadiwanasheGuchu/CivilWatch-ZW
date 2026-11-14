"""Council departments (e.g. Roads, Water and Sewerage)."""

import uuid

from sqlalchemy import Boolean, CheckConstraint, ForeignKey, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import CITEXT, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class Department(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "departments"

    council_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("councils.id", ondelete="RESTRICT"), nullable=False
    )
    name: Mapped[str] = mapped_column(CITEXT, nullable=False)
    description: Mapped[str | None] = mapped_column(String(240))
    is_active: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, server_default="true"
    )

    __table_args__ = (
        UniqueConstraint("council_id", "name", name="uq_departments_council_id_name"),
        # Lets other tables require "this department belongs to this council".
        UniqueConstraint("id", "council_id", name="uq_departments_id_council_id"),
        CheckConstraint("char_length(name) BETWEEN 2 AND 80", name="name_length"),
    )
