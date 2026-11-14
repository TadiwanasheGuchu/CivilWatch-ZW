"""Report categories, submission, the resident's own reports and public browsing."""

import uuid
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, File, Query, Request, Response, UploadFile, status

from app.api.deps import CurrentUser, DbDep, OptionalUser, SettingsDep, get_rate_limiter
from app.api.v1.issue_presenters import IssuePresenter
from app.core.rate_limit import RateLimiter
from app.core.storage import ObjectStorage, get_storage
from app.models.issues import IssueStatus
from app.schemas.issues import (
    CategoryRead,
    CreateIssueRequest,
    OwnIssue,
    OwnIssueDetail,
    PhotoRead,
    PublicIssue,
    PublicIssueDetail,
)
from app.schemas.pagination import Page, PageParams, page_params
from app.services.issues import IssueService
from app.services.photos import PhotoService

categories_router = APIRouter(prefix="/categories", tags=["issues"])
router = APIRouter(prefix="/issues", tags=["issues"])

PageDep = Annotated[PageParams, Depends(page_params)]
PublishedStatus = Literal["VERIFIED", "ASSIGNED", "IN_PROGRESS", "RESOLVED", "CLOSED"]


def get_issue_service(
    db: DbDep, settings: SettingsDep, limiter: Annotated[RateLimiter, Depends(get_rate_limiter)]
) -> IssueService:
    return IssueService(db, settings, limiter)


ServiceDep = Annotated[IssueService, Depends(get_issue_service)]
StorageDep = Annotated[ObjectStorage, Depends(get_storage)]


def get_presenter(storage: StorageDep, settings: SettingsDep) -> IssuePresenter:
    return IssuePresenter(storage, settings.media_url_ttl_seconds)


PresenterDep = Annotated[IssuePresenter, Depends(get_presenter)]


def get_photo_service(
    db: DbDep,
    settings: SettingsDep,
    storage: StorageDep,
    limiter: Annotated[RateLimiter, Depends(get_rate_limiter)],
) -> PhotoService:
    return PhotoService(db, settings, storage, limiter)


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
def submit_report(
    payload: CreateIssueRequest, user: CurrentUser, service: ServiceDep, present: PresenterDep
) -> OwnIssue:
    return present.own(service.submit(user, payload))


@router.get(
    "/mine",
    response_model=Page[OwnIssue],
    summary="Your reports, newest first",
    responses={401: {"description": "Not signed in"}},
)
def my_reports(
    user: CurrentUser, service: ServiceDep, present: PresenterDep, page: PageDep
) -> Page[OwnIssue]:
    items, total = service.list_mine(user, page)
    return Page(
        items=[present.own(i) for i in items],
        page=page.page,
        page_size=page.page_size,
        total=total,
    )


@router.get(
    "",
    response_model=Page[PublicIssue],
    summary="Published public reports, newest first",
)
def browse_reports(
    service: ServiceDep,
    present: PresenterDep,
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
        items=[present.public(i) for i in items],
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
    issue_id: uuid.UUID, viewer: OptionalUser, service: ServiceDep, present: PresenterDep
) -> OwnIssueDetail | PublicIssueDetail:
    view = service.get_for_viewer(issue_id, viewer)
    if view.viewer_is_reporter:
        return present.own_detail(view.issue, view.history)
    return present.public_detail(view.issue, view.history)


# Multipart framing overhead allowed on top of the photo itself.
_MULTIPART_OVERHEAD = 64 * 1024


@router.post(
    "/{issue_id}/photos",
    status_code=status.HTTP_201_CREATED,
    response_model=PhotoRead,
    summary="Add a photo to your report (JPEG, PNG or WebP)",
    responses={
        404: {"description": "Not your report"},
        409: {"description": "Report no longer accepts photos, or photo limit reached"},
        413: {"description": "Photo too large"},
        422: {"description": "Not a readable photo"},
        429: {"description": "Too many uploads"},
    },
)
def add_photo(
    issue_id: uuid.UUID,
    request: Request,
    user: CurrentUser,
    settings: SettingsDep,
    photos: Annotated[PhotoService, Depends(get_photo_service)],
    present: PresenterDep,
    file: Annotated[UploadFile, File(description="The photo")],
) -> PhotoRead:
    declared = request.headers.get("content-length", "")
    max_request = settings.photo_max_upload_bytes + _MULTIPART_OVERHEAD
    if declared.isdigit() and int(declared) > max_request:
        raise photos.too_large()
    # Read at most one byte past the limit, whatever the client claimed.
    data = file.file.read(settings.photo_max_upload_bytes + 1)
    return present.photo(photos.add_photo(user, issue_id, data))


@router.delete(
    "/{issue_id}/photos/{photo_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Remove a photo from your report while it awaits review",
    responses={
        404: {"description": "Not your report, or no such photo"},
        409: {"description": "The council has started on the report"},
    },
)
def remove_photo(
    issue_id: uuid.UUID,
    photo_id: uuid.UUID,
    user: CurrentUser,
    photos: Annotated[PhotoService, Depends(get_photo_service)],
) -> Response:
    photos.remove_photo(user, issue_id, photo_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
