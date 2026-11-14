"""Report categories, submission, the resident's own reports and public browsing."""

import uuid
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, Query, status

from app.api.deps import CurrentUser, DbDep, OptionalUser, SettingsDep, get_rate_limiter
from app.core.rate_limit import RateLimiter
from app.models.issues import Issue, IssueStatus
from app.schemas.issues import (
    CategoryRead,
    CreateIssueRequest,
    OwnIssue,
    OwnIssueDetail,
    PublicIssue,
    PublicIssueDetail,
    StatusChange,
)
from app.schemas.pagination import Page, PageParams, page_params
from app.services.issues import IssueService

categories_router = APIRouter(prefix="/categories", tags=["issues"])
router = APIRouter(prefix="/issues", tags=["issues"])

PageDep = Annotated[PageParams, Depends(page_params)]
PublishedStatus = Literal["VERIFIED", "ASSIGNED", "IN_PROGRESS", "RESOLVED", "CLOSED"]


def get_issue_service(
    db: DbDep, settings: SettingsDep, limiter: Annotated[RateLimiter, Depends(get_rate_limiter)]
) -> IssueService:
    return IssueService(db, settings, limiter)


ServiceDep = Annotated[IssueService, Depends(get_issue_service)]


def _own(issue: Issue) -> OwnIssue:
    return OwnIssue.model_validate(issue)


@categories_router.get("", response_model=list[CategoryRead], summary="Report categories")
def list_categories(service: ServiceDep) -> list[CategoryRead]:
    return [CategoryRead.model_validate(c) for c in service.list_categories()]


@router.post(
    "",
    status_code=status.HTTP_201_CREATED,
    response_model=OwnIssue,
    summary="Submit a report",
    responses={
        401: {"description": "Not signed in"},
        403: {"description": "CSRF token missing or invalid"},
        422: {"description": "Invalid report, council, category or location"},
        429: {"description": "Too many reports; see Retry-After"},
    },
)
def submit_report(payload: CreateIssueRequest, user: CurrentUser, service: ServiceDep) -> OwnIssue:
    return _own(service.submit(user, payload))


@router.get(
    "/mine",
    response_model=Page[OwnIssue],
    summary="Your reports, newest first",
    responses={401: {"description": "Not signed in"}},
)
def my_reports(user: CurrentUser, service: ServiceDep, page: PageDep) -> Page[OwnIssue]:
    items, total = service.list_mine(user, page)
    return Page(
        items=[_own(i) for i in items], page=page.page, page_size=page.page_size, total=total
    )


@router.get(
    "",
    response_model=Page[PublicIssue],
    summary="Published public reports, newest first",
)
def browse_reports(
    service: ServiceDep,
    page: PageDep,
    council_id: Annotated[uuid.UUID | None, Query()] = None,
    category: Annotated[str | None, Query(max_length=40, pattern=r"^[a-z0-9-]+$")] = None,
    status_filter: Annotated[PublishedStatus | None, Query(alias="status")] = None,
) -> Page[PublicIssue]:
    items, total = service.list_published(
        page,
        council_id=council_id,
        category_code=category,
        status=IssueStatus(status_filter) if status_filter else None,
    )
    return Page(
        items=[PublicIssue.model_validate(i) for i in items],
        page=page.page,
        page_size=page.page_size,
        total=total,
    )


@router.get(
    "/{issue_id}",
    response_model=OwnIssueDetail | PublicIssueDetail,
    summary="A report: your own (any visibility) or a published public one",
    responses={404: {"description": "Not found, or not visible to you"}},
)
def read_report(
    issue_id: uuid.UUID, viewer: OptionalUser, service: ServiceDep
) -> OwnIssueDetail | PublicIssueDetail:
    view = service.get_for_viewer(issue_id, viewer)
    history = [StatusChange.model_validate(h) for h in view.history]
    if view.viewer_is_reporter:
        return OwnIssueDetail(**_own(view.issue).model_dump(), history=history)
    return PublicIssueDetail(**PublicIssue.model_validate(view.issue).model_dump(), history=history)
