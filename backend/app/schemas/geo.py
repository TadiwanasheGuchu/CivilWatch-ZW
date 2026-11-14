import uuid
from typing import Any

from pydantic import BaseModel, ConfigDict

from app.models.councils import BoundarySource
from app.models.issues import IssueStatus
from app.schemas.issues import PublicIssue
from app.schemas.operations import StaffIssueSummary

# GeoJSON boundaries can be large; the request body limit is checked separately.
MAX_BOUNDARY_BYTES = 5 * 1024 * 1024


class LocatedCouncil(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    slug: str
    name: str
    is_sample_boundary: bool


class SetBoundaryRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    # A GeoJSON Polygon/MultiPolygon, Feature, or one-feature FeatureCollection,
    # with [longitude, latitude] coordinates in WGS 84.
    geometry: dict[str, Any]
    source: BoundarySource


class BoundaryResponse(BaseModel):
    council_id: uuid.UUID
    source: BoundarySource
    area_km2: float
    vertex_count: int
    # Other councils whose boundaries overlap this one; worth checking, not blocked.
    overlaps: list[str]


class ClusterRead(BaseModel):
    latitude: float
    longitude: float
    count: int
    # Present when the cluster is a single report.
    issue_id: uuid.UUID | None
    status: IssueStatus | None


class ClustersResponse(BaseModel):
    zoom: int
    clusters: list[ClusterRead]
    total: int


class NearbyPublicIssue(PublicIssue):
    distance_m: float


class NearbyStaffIssue(StaffIssueSummary):
    distance_m: float


def parse_bbox(value: str) -> tuple[float, float, float, float]:
    """`west,south,east,north` in degrees."""
    try:
        west, south, east, north = (float(part) for part in value.split(","))
    except ValueError as exc:
        raise ValueError("bbox must be west,south,east,north") from exc
    if not (-180 <= west < east <= 180 and -90 <= south < north <= 90):
        raise ValueError("bbox must be west,south,east,north within world bounds")
    return west, south, east, north
