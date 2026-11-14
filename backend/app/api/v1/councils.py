"""Council directory, workspaces, staff membership and audit trail."""

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Response, status

from app.api.deps import CouncilAccessDep, CurrentUser, DbDep
from app.models.councils import CouncilMembership
from app.schemas.councils import (
    AddMemberRequest,
    AuditLogRead,
    ChangeRoleRequest,
    CouncilSummary,
    CreateCouncilRequest,
    MemberRead,
    WorkspaceResponse,
)
from app.schemas.pagination import Page, PageParams, page_params
from app.services.councils import CouncilService

router = APIRouter(prefix="/councils", tags=["councils"])

PageDep = Annotated[PageParams, Depends(page_params)]

_ERRORS = {
    401: {"description": "Not signed in"},
    403: {"description": "Not a member, missing permission, or CSRF failure"},
    404: {"description": "Council or member not found"},
}


def get_council_service(db: DbDep) -> CouncilService:
    return CouncilService(db)


ServiceDep = Annotated[CouncilService, Depends(get_council_service)]


def _member_read(membership: CouncilMembership) -> MemberRead:
    return MemberRead(
        membership_id=membership.id,
        user_id=membership.user_id,
        full_name=membership.user.full_name,
        email=membership.user.email,
        role=membership.role,
        granted_at=membership.created_at,
    )


@router.get("", response_model=Page[CouncilSummary], summary="Public directory of councils")
def list_councils(service: ServiceDep, page: PageDep) -> Page[CouncilSummary]:
    items, total = service.list_public(page)
    return Page(
        items=[CouncilSummary.model_validate(c) for c in items],
        page=page.page,
        page_size=page.page_size,
        total=total,
    )


@router.post(
    "",
    status_code=status.HTTP_201_CREATED,
    response_model=CouncilSummary,
    summary="Create a council (platform administrators only)",
    responses={409: {"description": "Slug already in use"}, **_ERRORS},
)
def create_council(
    payload: CreateCouncilRequest, user: CurrentUser, service: ServiceDep
) -> CouncilSummary:
    council = service.create_council(user, slug=payload.slug, name=payload.name)
    return CouncilSummary.model_validate(council)


@router.get(
    "/{council_id}/workspace",
    response_model=WorkspaceResponse,
    summary="Your role and permissions in a council",
    responses=_ERRORS,
)
def workspace(access: CouncilAccessDep) -> WorkspaceResponse:
    return WorkspaceResponse(
        council=CouncilSummary.model_validate(access.council),
        role=access.role,
        via_platform_admin=access.via_platform_admin,
        permissions=sorted(access.permissions),
    )


@router.get(
    "/{council_id}/members",
    response_model=Page[MemberRead],
    summary="Council staff",
    responses=_ERRORS,
)
def list_members(access: CouncilAccessDep, service: ServiceDep, page: PageDep) -> Page[MemberRead]:
    items, total = service.list_members(access, page)
    return Page(
        items=[_member_read(m) for m in items],
        page=page.page,
        page_size=page.page_size,
        total=total,
    )


@router.post(
    "/{council_id}/members",
    status_code=status.HTTP_201_CREATED,
    response_model=MemberRead,
    summary="Add a registered user to council staff",
    responses={409: {"description": "Already a member"}, **_ERRORS},
)
def add_member(
    payload: AddMemberRequest, access: CouncilAccessDep, service: ServiceDep
) -> MemberRead:
    return _member_read(service.add_member(access, email=payload.email, role=payload.role))


@router.patch(
    "/{council_id}/members/{membership_id}",
    response_model=MemberRead,
    summary="Change a staff member's role",
    responses={409: {"description": "Would remove the last administrator"}, **_ERRORS},
)
def change_member_role(
    membership_id: uuid.UUID,
    payload: ChangeRoleRequest,
    access: CouncilAccessDep,
    service: ServiceDep,
) -> MemberRead:
    return _member_read(service.change_role(access, membership_id, role=payload.role))


@router.delete(
    "/{council_id}/members/{membership_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Remove a staff member (history is kept)",
    responses={409: {"description": "Would remove the last administrator"}, **_ERRORS},
)
def revoke_member(
    membership_id: uuid.UUID, access: CouncilAccessDep, service: ServiceDep
) -> Response:
    service.revoke_member(access, membership_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get(
    "/{council_id}/audit-logs",
    response_model=Page[AuditLogRead],
    summary="Council audit trail (council administrators)",
    responses=_ERRORS,
)
def list_audit_logs(
    access: CouncilAccessDep, service: ServiceDep, page: PageDep
) -> Page[AuditLogRead]:
    items, total = service.list_audit_logs(access, page)
    return Page(
        items=[AuditLogRead.model_validate(entry) for entry in items],
        page=page.page,
        page_size=page.page_size,
        total=total,
    )
