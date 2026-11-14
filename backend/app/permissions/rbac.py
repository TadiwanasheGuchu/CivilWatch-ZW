"""Role-based permissions within a council.

The backend is the only place permissions are decided. The frontend may
read a member's permission list to shape its UI, never to grant access.
New permissions are added here as features land (issues, assignments, …).
"""

from enum import StrEnum

from app.models.councils import CouncilRole


class Permission(StrEnum):
    WORKSPACE_VIEW = "workspace.view"
    MEMBERS_VIEW = "members.view"
    MEMBERS_MANAGE = "members.manage"
    AUDIT_VIEW = "audit.view"


_STAFF_BASELINE = frozenset({Permission.WORKSPACE_VIEW, Permission.MEMBERS_VIEW})

ROLE_PERMISSIONS: dict[CouncilRole, frozenset[Permission]] = {
    CouncilRole.COUNCIL_ADMIN: _STAFF_BASELINE | {Permission.MEMBERS_MANAGE, Permission.AUDIT_VIEW},
    CouncilRole.DEPARTMENT_MANAGER: _STAFF_BASELINE,
    CouncilRole.VERIFICATION_OFFICER: _STAFF_BASELINE,
    CouncilRole.MAINTENANCE_OFFICER: _STAFF_BASELINE,
}

# Platform admins without a membership may administer a council's staff
# (e.g. appoint its first administrator) but get no access to its
# operational data. Every such action is audited.
PLATFORM_ADMIN_COUNCIL_PERMISSIONS = frozenset(
    {Permission.MEMBERS_VIEW, Permission.MEMBERS_MANAGE, Permission.AUDIT_VIEW}
)


def permissions_for(role: CouncilRole | None, *, is_platform_admin: bool) -> frozenset[Permission]:
    granted = ROLE_PERMISSIONS[role] if role is not None else frozenset()
    if is_platform_admin:
        granted = granted | PLATFORM_ADMIN_COUNCIL_PERMISSIONS
    return granted
