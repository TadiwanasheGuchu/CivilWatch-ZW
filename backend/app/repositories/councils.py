"""Data access for councils, memberships and the audit trail.

Every query on council-owned data takes an explicit council_id. RLS is a
second line of defence, not a substitute for these filters.
"""

import uuid

from sqlalchemy import Select, func, select
from sqlalchemy.orm import Session

from app.models.audit import AuditLog
from app.models.councils import Council, CouncilMembership, CouncilRole
from app.models.identity import User


class CouncilRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def list_active(self, *, offset: int, limit: int) -> tuple[list[Council], int]:
        base = select(Council).where(Council.is_active.is_(True))
        total = self.db.scalar(select(func.count()).select_from(base.subquery())) or 0
        items = self.db.scalars(base.order_by(Council.name).offset(offset).limit(limit)).all()
        return list(items), total

    def slug_exists(self, slug: str) -> bool:
        return self.db.scalar(select(Council.id).where(Council.slug == slug)) is not None

    def add(self, council: Council) -> Council:
        self.db.add(council)
        self.db.flush()
        return council


class MembershipRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def _active(self) -> Select[tuple[CouncilMembership]]:
        return select(CouncilMembership).where(CouncilMembership.revoked_at.is_(None))

    def list_for_user(self, user_id: uuid.UUID) -> list[CouncilMembership]:
        stmt = (
            self._active()
            .join(CouncilMembership.council)
            .where(CouncilMembership.user_id == user_id, Council.is_active.is_(True))
            .order_by(Council.name)
        )
        return list(self.db.scalars(stmt).all())

    def list_for_council(
        self, council_id: uuid.UUID, *, offset: int, limit: int
    ) -> tuple[list[CouncilMembership], int]:
        base = self._active().where(CouncilMembership.council_id == council_id)
        total = self.db.scalar(select(func.count()).select_from(base.subquery())) or 0
        stmt = (
            base.join(CouncilMembership.user)
            .order_by(User.full_name, CouncilMembership.id)
            .offset(offset)
            .limit(limit)
        )
        return list(self.db.scalars(stmt).all()), total

    def get_active(
        self, council_id: uuid.UUID, membership_id: uuid.UUID
    ) -> CouncilMembership | None:
        return self.db.scalar(
            self._active().where(
                CouncilMembership.council_id == council_id, CouncilMembership.id == membership_id
            )
        )

    def get_active_for_user(
        self, council_id: uuid.UUID, user_id: uuid.UUID
    ) -> CouncilMembership | None:
        return self.db.scalar(
            self._active().where(
                CouncilMembership.council_id == council_id, CouncilMembership.user_id == user_id
            )
        )

    def count_admins(self, council_id: uuid.UUID, *, lock: bool = False) -> int:
        stmt = select(CouncilMembership.id).where(
            CouncilMembership.council_id == council_id,
            CouncilMembership.role == CouncilRole.COUNCIL_ADMIN,
            CouncilMembership.revoked_at.is_(None),
        )
        if lock:
            # Lock the administrators' rows so two concurrent demotions or
            # removals cannot both pass the "not the last admin" check.
            stmt = stmt.with_for_update()
        return len(self.db.scalars(stmt).all())

    def add(self, membership: CouncilMembership) -> CouncilMembership:
        self.db.add(membership)
        self.db.flush()
        return membership


class AuditRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def list_for_council(
        self, council_id: uuid.UUID, *, offset: int, limit: int
    ) -> tuple[list[AuditLog], int]:
        base = select(AuditLog).where(AuditLog.council_id == council_id)
        total = self.db.scalar(select(func.count()).select_from(base.subquery())) or 0
        stmt = base.order_by(AuditLog.occurred_at.desc(), AuditLog.id).offset(offset).limit(limit)
        return list(self.db.scalars(stmt).all()), total
