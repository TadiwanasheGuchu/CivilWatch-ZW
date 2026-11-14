"""Council staff endpoints: report queue, review and work, departments.

All routes are under /councils/{council_id}; access comes from the caller's
own membership of that council (see app/permissions/council_access.py).
"""

import uuid
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, File, Query, Request, UploadFile, status

from app.api.deps import CouncilAccessDep, DbDep, SettingsDep, get_rate_limiter
from app.api.v1.issue_presenters import IssuePresenter
from app.core.rate_limit import RateLimiter
from app.core.storage import ObjectStorage, get_storage
from app.models.issues import Issue, IssueStatus
from app.permissions.council_access import CouncilAccess
from app.repositories.operations import CurrentAssignment, QueueFilters
from app.schemas.issues import CategorySummary, PhotoRead
from app.schemas.operations import (
    AssignmentRead,
    AssignRequest,
    AvailableTransition,
    CreateDepartmentRequest,
    DepartmentRead,
    DepartmentRef,
    InternalUpdateRead,
    InternalUpdateRequest,
    IssueRef,
    PersonRef,
    QueueSummary,
    StaffIssueDetail,
    StaffIssueSummary,
    StaffStatusChange,
    StatusCount,
    TransitionRequest,
    UpdateDepartmentRequest,
)
from app.schemas.pagination import Page, PageParams, page_params
from app.services.departments import DepartmentService
from app.services.operations import CouncilIssueService, StaffIssueView
from app.services.photos import PhotoService

router = APIRouter(prefix="/councils/{council_id}", tags=["council operations"])

PageDep = Annotated[PageParams, Depends(page_params)]
_ERRORS = {
    401: {"description": "Not signed in"},
    403: {"description": "Not staff of this council, missing permission, or CSRF failure"},
    404: {"description": "Council, report or department not found"},
}


def get_issue_service(db: DbDep) -> CouncilIssueService:
    return CouncilIssueService(db)


def get_presenter(
    storage: Annotated[ObjectStorage, Depends(get_storage)], settings: SettingsDep
) -> IssuePresenter:
    return IssuePresenter(storage, settings.media_url_ttl_seconds)


IssuesDep = Annotated[CouncilIssueService, Depends(get_issue_service)]
PresenterDep = Annotated[IssuePresenter, Depends(get_presenter)]


def _assignment(current: CurrentAssignment | None) -> AssignmentRead | None:
    if current is None:
        return None
    a = current.assignment
    return AssignmentRead(
        department=DepartmentRef(id=a.department_id, name=current.department_name),
        assignee=(
            PersonRef(id=a.assignee_user_id, full_name=current.assignee_name or "Unknown")
            if a.assignee_user_id
            else None
        ),
        assigned_at=a.created_at,
    )


def _summary(issue: Issue, current: CurrentAssignment | None, present: IssuePresenter) -> dict:
    own = present.own(issue)
    return {
        "id": issue.id,
        "reference": issue.reference,
        "title": issue.title,
        "category": CategorySummary.model_validate(issue.category),
        "status": issue.status,
        "visibility": issue.visibility,
        "location_description": issue.location_description,
        "latitude": issue.latitude,
        "longitude": issue.longitude,
        "created_at": issue.created_at,
        "updated_at": issue.updated_at,
        "photo_count": own.photo_count,
        "cover_thumbnail_url": own.cover_thumbnail_url,
        "assignment": _assignment(current),
    }


def _detail(view: StaffIssueView, present: IssuePresenter) -> StaffIssueDetail:
    issue = view.issue
    return StaffIssueDetail(
        **_summary(issue, view.assignment, present),
        description=issue.description,
        reporter_name=view.reporter_name,
        duplicate_of=(
            IssueRef(id=view.duplicate_of.id, reference=view.duplicate_of.reference)
            if view.duplicate_of
            else None
        ),
        photos=[present.photo(m) for m in issue.report_photos],
        repair_photos=[present.photo(m) for m in issue.repair_photos],
        history=[
            StaffStatusChange(
                from_status=h.from_status,
                to_status=h.to_status,
                note=h.note,
                changed_by=name,
                created_at=h.created_at,
            )
            for h, name in view.history
        ],
        updates=[
            InternalUpdateRead(id=u.id, body=u.body, author=name, created_at=u.created_at)
            for u, name in view.updates
        ],
        available_transitions=[
            AvailableTransition(
                to_status=to_status,
                label=t.label,
                note_required=t.note_required,
                needs_duplicate_of=t.needs_duplicate_of,
            )
            for to_status, t in view.transitions
        ],
        can_assign=view.can_assign,
        can_add_repair_photos=view.can_add_repair_photos,
    )


def _respond_detail(
    access: CouncilAccess,
    issue_id: uuid.UUID,
    service: CouncilIssueService,
    present: IssuePresenter,
) -> StaffIssueDetail:
    return _detail(service.detail(access, issue_id), present)


# --- Reports ---------------------------------------------------------------------------------


@router.get(
    "/issues/summary", response_model=QueueSummary, summary="Report counts", responses=_ERRORS
)
def queue_summary(access: CouncilAccessDep, service: IssuesDep) -> QueueSummary:
    counts, mine = service.summary(access)
    return QueueSummary(
        counts=[StatusCount(status=s, count=counts.get(s, 0)) for s in IssueStatus],
        assigned_to_me=mine,
    )


@router.get(
    "/issues",
    response_model=Page[StaffIssueSummary],
    summary="Council report queue",
    responses=_ERRORS,
)
def council_queue(
    access: CouncilAccessDep,
    service: IssuesDep,
    present: PresenterDep,
    page: PageDep,
    status_filter: Annotated[list[IssueStatus] | None, Query(alias="status")] = None,
    category: Annotated[str | None, Query(max_length=40, pattern=r"^[a-z0-9-]+$")] = None,
    department_id: uuid.UUID | None = None,
    assigned_to_me: bool = False,
    q: Annotated[str | None, Query(max_length=100)] = None,
    sort: Literal["newest", "oldest"] = "newest",
) -> Page[StaffIssueSummary]:
    filters = QueueFilters(
        statuses=tuple(status_filter or ()),
        category_code=category,
        department_id=department_id,
        assignee_user_id=access.user.id if assigned_to_me else None,
        search=q.strip() if q and q.strip() else None,
        oldest_first=sort == "oldest",
    )
    items, assignments, total = service.queue(access, filters, page)
    return Page(
        items=[StaffIssueSummary(**_summary(i, assignments.get(i.id), present)) for i in items],
        page=page.page,
        page_size=page.page_size,
        total=total,
    )


@router.get(
    "/issues/{issue_id}",
    response_model=StaffIssueDetail,
    summary="A report, for staff",
    responses=_ERRORS,
)
def council_issue(
    issue_id: uuid.UUID, access: CouncilAccessDep, service: IssuesDep, present: PresenterDep
) -> StaffIssueDetail:
    return _respond_detail(access, issue_id, service, present)


@router.post(
    "/issues/{issue_id}/transitions",
    response_model=StaffIssueDetail,
    summary="Change a report's status",
    responses={409: {"description": "Not allowed from the current status"}, **_ERRORS},
)
def change_status(
    issue_id: uuid.UUID,
    payload: TransitionRequest,
    access: CouncilAccessDep,
    service: IssuesDep,
    present: PresenterDep,
) -> StaffIssueDetail:
    service.transition(access, issue_id, payload)
    return _respond_detail(access, issue_id, service, present)


@router.post(
    "/issues/{issue_id}/assignment",
    response_model=StaffIssueDetail,
    summary="Assign or reassign a report to a department and officer",
    responses={409: {"description": "Report is not verified yet"}, **_ERRORS},
)
def assign_issue(
    issue_id: uuid.UUID,
    payload: AssignRequest,
    access: CouncilAccessDep,
    service: IssuesDep,
    present: PresenterDep,
) -> StaffIssueDetail:
    service.assign(access, issue_id, payload)
    return _respond_detail(access, issue_id, service, present)


@router.post(
    "/issues/{issue_id}/updates",
    response_model=StaffIssueDetail,
    status_code=status.HTTP_201_CREATED,
    summary="Add a staff-only note",
    responses=_ERRORS,
)
def add_internal_update(
    issue_id: uuid.UUID,
    payload: InternalUpdateRequest,
    access: CouncilAccessDep,
    service: IssuesDep,
    present: PresenterDep,
) -> StaffIssueDetail:
    service.add_update(access, issue_id, payload.body)
    return _respond_detail(access, issue_id, service, present)


_MULTIPART_OVERHEAD = 64 * 1024


def get_photo_service(
    db: DbDep,
    settings: SettingsDep,
    storage: Annotated[ObjectStorage, Depends(get_storage)],
    limiter: Annotated[RateLimiter, Depends(get_rate_limiter)],
) -> PhotoService:
    return PhotoService(db, settings, storage, limiter)


@router.post(
    "/issues/{issue_id}/photos",
    response_model=PhotoRead,
    status_code=status.HTTP_201_CREATED,
    summary="Add a repair evidence photo (staff doing the work)",
    responses={
        409: {"description": "Work is not in progress or resolved, or photo limit reached"},
        413: {"description": "Photo too large"},
        422: {"description": "Not a readable photo"},
        **_ERRORS,
    },
)
def add_repair_photo(
    issue_id: uuid.UUID,
    request: Request,
    access: CouncilAccessDep,
    settings: SettingsDep,
    photos: Annotated[PhotoService, Depends(get_photo_service)],
    present: PresenterDep,
    file: Annotated[UploadFile, File(description="The photo")],
) -> PhotoRead:
    declared = request.headers.get("content-length", "")
    if declared.isdigit() and int(declared) > settings.photo_max_upload_bytes + _MULTIPART_OVERHEAD:
        raise photos.too_large()
    data = file.file.read(settings.photo_max_upload_bytes + 1)
    return present.photo(photos.add_repair_photo(access, issue_id, data))


# --- Departments ----------------------------------------------------------------------------------


def get_department_service(db: DbDep) -> DepartmentService:
    return DepartmentService(db)


DepartmentsDep = Annotated[DepartmentService, Depends(get_department_service)]


@router.get(
    "/departments", response_model=list[DepartmentRead], summary="Departments", responses=_ERRORS
)
def list_departments(access: CouncilAccessDep, service: DepartmentsDep) -> list[DepartmentRead]:
    return [DepartmentRead.model_validate(d) for d in service.list(access)]


@router.post(
    "/departments",
    response_model=DepartmentRead,
    status_code=status.HTTP_201_CREATED,
    summary="Create a department (council administrators)",
    responses={409: {"description": "Name already used"}, **_ERRORS},
)
def create_department(
    payload: CreateDepartmentRequest, access: CouncilAccessDep, service: DepartmentsDep
) -> DepartmentRead:
    return DepartmentRead.model_validate(service.create(access, payload))


@router.patch(
    "/departments/{department_id}",
    response_model=DepartmentRead,
    summary="Rename, describe, or deactivate a department",
    responses={409: {"description": "Name already used"}, **_ERRORS},
)
def update_department(
    department_id: uuid.UUID,
    payload: UpdateDepartmentRequest,
    access: CouncilAccessDep,
    service: DepartmentsDep,
) -> DepartmentRead:
    return DepartmentRead.model_validate(service.update(access, department_id, payload))
