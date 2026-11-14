"""Councils and staff membership management."""

import uuid
from datetime import UTC, datetime

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.errors import AppError, ConflictError, NotFoundError, PermissionDeniedError
from app.models.audit import AuditLog
from app.models.councils import Council, CouncilMembership, CouncilRole
from app.models.identity import User
from app.permissions.council_access import CouncilAccess
from app.permissions.rbac import Permission
from app.repositories.councils import AuditRepository, CouncilRepository, MembershipRepository
from app.repositories.identity import UserRepository
from app.schemas.pagination import PageParams
from app.services.audit import record_audit


class LastAdministratorError(AppError):
    status_code = 409
    code = "last_council_admin"


class CouncilService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.councils = CouncilRepository(db)
        self.memberships = MembershipRepository(db)
        self.audit = AuditRepository(db)
        self.users = UserRepository(db)

    # --- Councils ---------------------------------------------------------------

    def list_public(self, page: PageParams) -> tuple[list[Council], int]:
        return self.councils.list_active(offset=page.offset, limit=page.page_size)

    def create_council(self, actor: User, *, slug: str, name: str) -> Council:
        if not actor.is_platform_admin:
            raise PermissionDeniedError("Only platform administrators can create councils.")
        if self.councils.slug_exists(slug):
            raise ConflictError("A council with this identifier already exists.")
        council = Council(slug=slug, name=name)
        try:
            self.councils.add(council)
            record_audit(
                self.db,
                action="council.created",
                actor_user_id=actor.id,
                council_id=council.id,
                target_type="council",
                target_id=council.id,
                details={"slug": slug, "name": name},
            )
            self.db.commit()
        except IntegrityError as exc:
            self.db.rollback()
            raise ConflictError("A council with this identifier already exists.") from exc
        return council

    # --- Memberships ----------------------------------------------------------------

    def list_my_memberships(self, user: User) -> list[CouncilMembership]:
        return self.memberships.list_for_user(user.id)

    def list_members(
        self, access: CouncilAccess, page: PageParams
    ) -> tuple[list[CouncilMembership], int]:
        access.require(Permission.MEMBERS_VIEW)
        return self.memberships.list_for_council(
            access.council.id, offset=page.offset, limit=page.page_size
        )

    def add_member(
        self, access: CouncilAccess, *, email: str, role: CouncilRole
    ) -> CouncilMembership:
        access.require(Permission.MEMBERS_MANAGE)
        user = self.users.get_by_email(email.strip().lower())
        if user is None or not user.is_active:
            raise NotFoundError(
                "No active CivicWatch account uses this email. Ask the person to register first."
            )
        if self.memberships.get_active_for_user(access.council.id, user.id) is not None:
            raise ConflictError("This person is already a member of the council.")
        membership = CouncilMembership(
            council_id=access.council.id,
            user_id=user.id,
            role=role,
            granted_by_user_id=access.user.id,
        )
        try:
            self.memberships.add(membership)
            self._audit(access, "membership.granted", membership, {"role": role.value})
            self.db.commit()
        except IntegrityError as exc:
            self.db.rollback()
            raise ConflictError("This person is already a member of the council.") from exc
        return membership

    def change_role(
        self, access: CouncilAccess, membership_id: uuid.UUID, *, role: CouncilRole
    ) -> CouncilMembership:
        access.require(Permission.MEMBERS_MANAGE)
        membership = self._get_member(access, membership_id)
        previous = membership.role
        if previous == role:
            return membership
        if previous == CouncilRole.COUNCIL_ADMIN:
            self._ensure_not_last_admin(access)
        membership.role = role
        self._audit(
            access, "membership.role_changed", membership, {"from": str(previous), "to": role.value}
        )
        self.db.commit()
        return membership

    def revoke_member(self, access: CouncilAccess, membership_id: uuid.UUID) -> None:
        access.require(Permission.MEMBERS_MANAGE)
        membership = self._get_member(access, membership_id)
        if membership.role == CouncilRole.COUNCIL_ADMIN:
            self._ensure_not_last_admin(access)
        membership.revoked_at = datetime.now(UTC)
        self._audit(access, "membership.revoked", membership, {"role": str(membership.role)})
        self.db.commit()

    # --- Audit --------------------------------------------------------------------------

    def list_audit_logs(
        self, access: CouncilAccess, page: PageParams
    ) -> tuple[list[tuple[AuditLog, str | None]], int]:
        access.require(Permission.AUDIT_VIEW)
        return self.audit.list_for_council(
            access.council.id, offset=page.offset, limit=page.page_size
        )

    # --- Internals -------------------------------------------------------------------------

    def _get_member(self, access: CouncilAccess, membership_id: uuid.UUID) -> CouncilMembership:
        membership = self.memberships.get_active(access.council.id, membership_id)
        if membership is None:
            raise NotFoundError("Member not found.")
        return membership

    def _ensure_not_last_admin(self, access: CouncilAccess) -> None:
        if self.memberships.count_admins(access.council.id, lock=True) <= 1:
            raise LastAdministratorError(
                "A council must keep at least one administrator. Appoint another first."
            )

    def _audit(
        self, access: CouncilAccess, action: str, membership: CouncilMembership, details: dict
    ) -> None:
        record_audit(
            self.db,
            action=action,
            actor_user_id=access.user.id,
            council_id=access.council.id,
            target_type="council_membership",
            target_id=membership.id,
            details={
                **details,
                "member_user_id": str(membership.user_id),
                "via_platform_admin": access.via_platform_admin,
            },
        )
