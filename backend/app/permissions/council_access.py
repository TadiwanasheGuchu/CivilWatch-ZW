"""Resolve what the current user may do in a council.

The council comes from the URL, but access is derived only from the
authenticated user's own active membership (or platform-admin flag) — a
council ID supplied by the client never grants anything by itself.
"""

import uuid
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.errors import NotFoundError, PermissionDeniedError
from app.models.councils import Council, CouncilMembership, CouncilRole
from app.models.identity import User
from app.permissions.rbac import Permission, permissions_for


@dataclass(frozen=True)
class CouncilAccess:
    council: Council
    user: User
    membership: CouncilMembership | None
    permissions: frozenset[Permission]

    @property
    def role(self) -> CouncilRole | None:
        return self.membership.role if self.membership else None

    @property
    def via_platform_admin(self) -> bool:
        """True when the platform-admin flag, not a membership, grants this access."""
        return self.membership is None and self.user.is_platform_admin

    def require(self, permission: Permission) -> None:
        if permission not in self.permissions:
            raise PermissionDeniedError("You do not have permission to do this in this council.")


def resolve_council_access(db: Session, user: User, council_id: uuid.UUID) -> CouncilAccess:
    council = db.get(Council, council_id)
    if council is None or not council.is_active:
        raise NotFoundError("Council not found.")
    membership = db.scalar(
        select(CouncilMembership).where(
            CouncilMembership.council_id == council_id,
            CouncilMembership.user_id == user.id,
            CouncilMembership.revoked_at.is_(None),
        )
    )
    permissions = permissions_for(
        membership.role if membership else None, is_platform_admin=user.is_platform_admin
    )
    if not permissions:
        raise PermissionDeniedError("You are not a member of this council.")
    return CouncilAccess(council=council, user=user, membership=membership, permissions=permissions)
