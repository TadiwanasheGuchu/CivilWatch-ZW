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
    DEPARTMENTS_MANAGE = "departments.manage"
    ISSUES_VIEW = "issues.view"
    ISSUES_REVIEW = "issues.review"
    ISSUES_ASSIGN = "issues.assign"
    ISSUES_WORK = "issues.work"
    ISSUES_CLOSE = "issues.close"


_STAFF_BASELINE = frozenset(
    {Permission.WORKSPACE_VIEW, Permission.MEMBERS_VIEW, Permission.ISSUES_VIEW}
)

# Agreed before Milestone 3: verification officers review; department
# managers assign and close within their department; maintenance officers
# carry out work assigned to them; council administrators can do everything.
# Department and assignee scoping is applied in app/services/workflow.py.
ROLE_PERMISSIONS: dict[CouncilRole, frozenset[Permission]] = {
    CouncilRole.COUNCIL_ADMIN: _STAFF_BASELINE
    | {
        Permission.MEMBERS_MANAGE,
        Permission.AUDIT_VIEW,
        Permission.DEPARTMENTS_MANAGE,
        Permission.ISSUES_REVIEW,
        Permission.ISSUES_ASSIGN,
        Permission.ISSUES_WORK,
        Permission.ISSUES_CLOSE,
    },
    CouncilRole.DEPARTMENT_MANAGER: _STAFF_BASELINE
    | {Permission.ISSUES_ASSIGN, Permission.ISSUES_WORK, Permission.ISSUES_CLOSE},
    CouncilRole.VERIFICATION_OFFICER: _STAFF_BASELINE | {Permission.ISSUES_REVIEW},
    CouncilRole.MAINTENANCE_OFFICER: _STAFF_BASELINE | {Permission.ISSUES_WORK},
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
