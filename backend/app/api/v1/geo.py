"""Maps and places: boundaries, locating a council, clusters, nearby reports."""

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response, status

from app.api.deps import CouncilAccessDep, CurrentUser, DbDep, SettingsDep
from app.api.v1.issue_presenters import IssuePresenter
from app.api.v1.operations import _summary, get_presenter
from app.models.councils import BoundarySource
from app.models.issues import IssueStatus
from app.permissions.rbac import Permission
from app.repositories.operations import OperationsRepository
from app.schemas.geo import (
    MAX_BOUNDARY_BYTES,
    BoundaryResponse,
    ClusterRead,
    ClustersResponse,
    LocatedCouncil,
    NearbyPublicIssue,
    NearbyStaffIssue,
    SetBoundaryRequest,
    parse_bbox,
)
from app.schemas.operations import StaffIssueSummary
from app.services.geo import BoundaryService, Cluster, MapFilters, MapService

router = APIRouter(tags=["maps"])

PresenterDep = Annotated[IssuePresenter, Depends(get_presenter)]
Latitude = Annotated[float, Query(ge=-90, le=90)]
Longitude = Annotated[float, Query(ge=-180, le=180)]
Zoom = Annotated[int, Query(ge=0, le=22)]
CategoryCode = Annotated[str | None, Query(max_length=40, pattern=r"^[a-z0-9-]+$")]


def _bbox(
    bbox: Annotated[str, Query(description="west,south,east,north")],
) -> tuple[float, float, float, float]:
    try:
        return parse_bbox(bbox)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


BBoxDep = Annotated[tuple[float, float, float, float], Depends(_bbox)]


def _clusters_response(zoom: int, clusters: list[Cluster], total: int) -> ClustersResponse:
    return ClustersResponse(
        zoom=zoom,
        total=total,
        clusters=[
            ClusterRead(
                latitude=c.latitude,
                longitude=c.longitude,
                count=c.count,
                issue_id=c.issue_id,
                status=c.status,
            )
            for c in clusters
        ],
    )


# --- Council boundaries ---


@router.get(
    "/councils/boundaries",
    summary="Council boundaries (GeoJSON FeatureCollection, simplified)",
    response_description="Features carry id, slug, name and is_sample",
)
def council_boundaries(response: Response, db: DbDep, settings: SettingsDep) -> dict:
    response.headers["Cache-Control"] = "public, max-age=300"
    return BoundaryService(db, settings).boundaries_geojson()


@router.get(
    "/councils/locate",
    response_model=list[LocatedCouncil],
    summary="Councils whose boundary covers a point (smallest first)",
)
def locate_council(
    latitude: Latitude, longitude: Longitude, db: DbDep, settings: SettingsDep
) -> list[LocatedCouncil]:
    return [
        LocatedCouncil(
            id=c.id,
            slug=c.slug,
            name=c.name,
            is_sample_boundary=c.boundary_source == BoundarySource.SAMPLE,
        )
        for c in BoundaryService(db, settings).locate(latitude, longitude)
    ]


@router.put(
    "/councils/{council_id}/boundary",
    response_model=BoundaryResponse,
    summary="Set a council's boundary from GeoJSON (platform administrators)",
    responses={
        403: {"description": "Not a platform administrator"},
        413: {"description": "Too large"},
    },
)
def set_boundary(
    council_id: uuid.UUID,
    payload: SetBoundaryRequest,
    request: Request,
    user: CurrentUser,
    db: DbDep,
    settings: SettingsDep,
) -> BoundaryResponse:
    declared = request.headers.get("content-length", "")
    if declared.isdigit() and int(declared) > MAX_BOUNDARY_BYTES:
        raise HTTPException(status_code=413, detail="Boundary files must be smaller than 5 MB.")
    result = BoundaryService(db, settings).set_boundary(
        user, council_id, payload.geometry, payload.source
    )
    return BoundaryResponse(
        council_id=result.council.id,
        source=payload.source,
        area_km2=result.area_km2,
        vertex_count=result.vertex_count,
        overlaps=result.overlaps,
    )


@router.delete(
    "/councils/{council_id}/boundary",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Remove a council's boundary (platform administrators)",
)
def clear_boundary(
    council_id: uuid.UUID, user: CurrentUser, db: DbDep, settings: SettingsDep
) -> Response:
    BoundaryService(db, settings).clear_boundary(user, council_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


# --- Public map ---


@router.get(
    "/map/clusters", response_model=ClustersResponse, summary="Clusters of published public reports"
)
def public_clusters(
    bbox: BBoxDep,
    zoom: Zoom,
    db: DbDep,
    council_id: uuid.UUID | None = None,
    category: CategoryCode = None,
    status_filter: Annotated[list[IssueStatus] | None, Query(alias="status")] = None,
) -> ClustersResponse:
    filters = MapFilters(
        council_id=council_id, category_code=category, statuses=tuple(status_filter or ())
    )
    clusters, total = MapService(db).clusters(bbox, zoom, filters, published_only=True)
    return _clusters_response(zoom, clusters, total)


@router.get(
    "/issues/nearby",
    response_model=list[NearbyPublicIssue],
    summary="Published public reports near a point, closest first",
)
def nearby_reports(
    latitude: Latitude,
    longitude: Longitude,
    db: DbDep,
    present: PresenterDep,
    radius_m: Annotated[int, Query(ge=25, le=5000)] = 500,
    category: CategoryCode = None,
    limit: Annotated[int, Query(ge=1, le=50)] = 20,
) -> list[NearbyPublicIssue]:
    rows = MapService(db).nearby_published(
        latitude, longitude, radius_m, category_code=category, limit=limit
    )
    return [
        NearbyPublicIssue(**present.public(issue).model_dump(), distance_m=round(distance, 1))
        for issue, distance in rows
    ]


# --- Council staff ---


@router.get(
    "/councils/{council_id}/map/clusters",
    response_model=ClustersResponse,
    summary="Clusters of this council's reports, any visibility (staff)",
)
def council_clusters(
    access: CouncilAccessDep,
    bbox: BBoxDep,
    zoom: Zoom,
    db: DbDep,
    category: CategoryCode = None,
    status_filter: Annotated[list[IssueStatus] | None, Query(alias="status")] = None,
) -> ClustersResponse:
    access.require(Permission.ISSUES_VIEW)
    filters = MapFilters(
        council_id=access.council.id, category_code=category, statuses=tuple(status_filter or ())
    )
    clusters, total = MapService(db).clusters(bbox, zoom, filters, published_only=False)
    return _clusters_response(zoom, clusters, total)


@router.get(
    "/councils/{council_id}/issues/{issue_id}/nearby",
    response_model=list[NearbyStaffIssue],
    summary="Other reports near this one, for spotting duplicates (staff)",
)
def nearby_for_staff(
    issue_id: uuid.UUID,
    access: CouncilAccessDep,
    db: DbDep,
    present: PresenterDep,
    radius_m: Annotated[int, Query(ge=25, le=2000)] = 200,
    limit: Annotated[int, Query(ge=1, le=50)] = 10,
) -> list[NearbyStaffIssue]:
    rows = MapService(db).nearby_for_staff(access, issue_id, radius_m, limit)
    assignments = OperationsRepository(db).current_assignments([issue.id for issue, _ in rows])
    return [
        NearbyStaffIssue(
            **StaffIssueSummary(**_summary(issue, assignments.get(issue.id), present)).model_dump(),
            distance_m=round(distance, 1),
        )
        for issue, distance in rows
    ]
