"""Geographic features: council boundaries, locating a council, map clusters, nearby reports.

All geometry work happens in PostGIS. Clustering is done in the database so
a phone receives a few hundred clusters rather than thousands of points.
"""

import json
import logging
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from geoalchemy2 import Geography, Geometry
from sqlalchemy import Select, String, and_, cast, func, select
from sqlalchemy.exc import DBAPIError
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.core.errors import FieldValidationError, NotFoundError, PermissionDeniedError
from app.models.councils import BoundarySource, Council
from app.models.identity import User
from app.models.issues import (
    PUBLISHED_STATUSES,
    Issue,
    IssueCategory,
    IssueStatus,
    IssueVisibility,
)
from app.permissions.council_access import CouncilAccess
from app.permissions.rbac import Permission
from app.services.audit import record_audit

logger = logging.getLogger(__name__)

MAX_BOUNDARY_VERTICES = 100_000
# ~100 m at Zimbabwe's latitude: plenty for drawing, far smaller to send.
BOUNDARY_DISPLAY_TOLERANCE = 0.001
MAX_CLUSTERS = 2_000


@dataclass(frozen=True)
class BoundaryResult:
    council: Council
    area_km2: float
    vertex_count: int
    overlaps: list[str]


@dataclass(frozen=True)
class Cluster:
    latitude: float
    longitude: float
    count: int
    issue_id: uuid.UUID | None
    status: IssueStatus | None


@dataclass(frozen=True)
class MapFilters:
    council_id: uuid.UUID | None = None
    category_code: str | None = None
    statuses: tuple[IssueStatus, ...] = ()


def point(latitude: float, longitude: float):  # SQL expression for a WGS 84 point
    return func.ST_SetSRID(func.ST_MakePoint(longitude, latitude), 4326)


def _extract_geometry(payload: dict[str, Any]) -> dict[str, Any]:
    """Accept a GeoJSON geometry, Feature, or single-feature FeatureCollection."""
    kind = payload.get("type")
    if kind == "FeatureCollection":
        features = payload.get("features") or []
        if len(features) != 1:
            raise FieldValidationError("geometry", "Upload one feature: the council's boundary.")
        payload = features[0]
        kind = payload.get("type")
    if kind == "Feature":
        payload = payload.get("geometry") or {}
        kind = payload.get("type")
    if kind not in ("Polygon", "MultiPolygon"):
        raise FieldValidationError("geometry", "The boundary must be a Polygon or MultiPolygon.")
    return payload


class BoundaryService:
    def __init__(self, db: Session, settings: Settings) -> None:
        self.db = db
        self.settings = settings

    # --- Reading ---

    def boundaries_geojson(self) -> dict[str, Any]:
        """Simplified boundaries of active councils, as a GeoJSON FeatureCollection."""
        rows = self.db.execute(
            select(
                Council.id,
                Council.slug,
                Council.name,
                Council.boundary_source,
                # Always MultiPolygon, so clients handle one geometry type.
                func.ST_AsGeoJSON(
                    func.ST_Multi(
                        func.ST_SimplifyPreserveTopology(
                            Council.boundary, BOUNDARY_DISPLAY_TOLERANCE
                        )
                    ),
                    5,
                ),
            )
            .where(Council.is_active.is_(True), Council.boundary.is_not(None))
            .order_by(Council.name)
        ).all()
        return {
            "type": "FeatureCollection",
            "features": [
                {
                    "type": "Feature",
                    "id": str(council_id),
                    "properties": {
                        "id": str(council_id),
                        "slug": slug,
                        "name": name,
                        "is_sample": source == BoundarySource.SAMPLE,
                    },
                    "geometry": json.loads(geometry),
                }
                for council_id, slug, name, source, geometry in rows
            ],
        }

    def locate(self, latitude: float, longitude: float) -> list[Council]:
        """Active councils whose boundary covers the point, smallest area first."""
        here = point(latitude, longitude)
        return list(
            self.db.scalars(
                select(Council)
                .where(
                    Council.is_active.is_(True),
                    Council.boundary.is_not(None),
                    func.ST_Covers(Council.boundary, here),
                )
                .order_by(func.ST_Area(Council.boundary))
            ).all()
        )

    # --- Changing (platform administrators) ---

    def set_boundary(
        self,
        actor: User | None,
        council_id: uuid.UUID,
        payload: dict[str, Any],
        source: BoundarySource,
        *,
        via: str = "api",
    ) -> BoundaryResult:
        # The operator command (via="cli") has no user; the API always does.
        if via == "api" and (actor is None or not actor.is_platform_admin):
            raise PermissionDeniedError(
                "Only platform administrators can change council boundaries."
            )
        council = self.db.get(Council, council_id)
        if council is None:
            raise NotFoundError("Council not found.")
        geometry = func.ST_Multi(
            func.ST_SetSRID(func.ST_GeomFromGeoJSON(json.dumps(_extract_geometry(payload))), 4326)
        )
        west, south, east, north = self.settings.service_area_bbox
        try:
            valid, reason, vertices, area_m2, inside = self.db.execute(
                select(
                    func.ST_IsValid(geometry),
                    func.ST_IsValidReason(geometry),
                    func.ST_NPoints(geometry),
                    func.ST_Area(cast(geometry, Geography)),
                    func.ST_CoveredBy(
                        geometry, func.ST_MakeEnvelope(west, south, east, north, 4326)
                    ),
                )
            ).one()
        except DBAPIError as exc:
            self.db.rollback()
            raise FieldValidationError("geometry", "This is not valid GeoJSON geometry.") from exc
        if not valid:
            raise FieldValidationError("geometry", f"The boundary shape is invalid: {reason}.")
        if vertices > MAX_BOUNDARY_VERTICES:
            raise FieldValidationError(
                "geometry", f"The boundary has too many points (limit {MAX_BOUNDARY_VERTICES:,})."
            )
        if not inside:
            raise FieldValidationError(
                "geometry",
                "The boundary is outside the area CivilWatch serves. GeoJSON coordinates are "
                "[longitude, latitude]; check they are not swapped.",
            )
        if area_m2 <= 0:
            raise FieldValidationError("geometry", "The boundary has no area.")

        council.boundary = geometry
        council.boundary_source = source
        council.boundary_updated_at = datetime.now(UTC)
        self.db.flush()
        overlaps = list(
            self.db.scalars(
                select(Council.name).where(
                    Council.id != council.id,
                    Council.boundary.is_not(None),
                    func.ST_Area(
                        func.ST_Intersection(
                            Council.boundary,
                            select(Council.boundary)
                            .where(Council.id == council.id)
                            .scalar_subquery(),
                        )
                    )
                    > 0,
                )
            ).all()
        )
        record_audit(
            self.db,
            action="council.boundary_set",
            actor_user_id=actor.id if actor is not None else None,
            council_id=council.id,
            target_type="council",
            target_id=council.id,
            details={
                "source": source.value,
                "area_km2": round(area_m2 / 1_000_000, 2),
                "vertices": vertices,
                "overlaps": overlaps,
                "via": via,
            },
        )
        self.db.commit()
        return BoundaryResult(council, round(area_m2 / 1_000_000, 2), vertices, overlaps)

    def clear_boundary(self, actor: User, council_id: uuid.UUID) -> None:
        if not actor.is_platform_admin:
            raise PermissionDeniedError(
                "Only platform administrators can change council boundaries."
            )
        council = self.db.get(Council, council_id)
        if council is None:
            raise NotFoundError("Council not found.")
        council.boundary = None
        council.boundary_source = None
        council.boundary_updated_at = datetime.now(UTC)
        record_audit(
            self.db,
            action="council.boundary_cleared",
            actor_user_id=actor.id,
            council_id=council.id,
            target_type="council",
            target_id=council.id,
        )
        self.db.commit()


def cell_size_degrees(zoom: int) -> float:
    """Grid cell for clustering: about a quarter of a 256 px map tile at this zoom."""
    return (360.0 / (2**zoom)) / 4


class MapService:
    def __init__(self, db: Session) -> None:
        self.db = db

    def _apply_filters(self, stmt: Select, filters: MapFilters) -> Select:
        if filters.council_id:
            stmt = stmt.where(Issue.council_id == filters.council_id)
        if filters.category_code:
            stmt = stmt.join(IssueCategory, IssueCategory.id == Issue.category_id).where(
                IssueCategory.code == filters.category_code
            )
        if filters.statuses:
            stmt = stmt.where(Issue.status.in_(filters.statuses))
        return stmt

    def clusters(
        self,
        bbox: tuple[float, float, float, float],
        zoom: int,
        filters: MapFilters,
        *,
        published_only: bool,
    ) -> tuple[list[Cluster], int]:
        west, south, east, north = bbox
        envelope = cast(func.ST_MakeEnvelope(west, south, east, north, 4326), Geography)
        geom = cast(Issue.location, Geometry)
        inner = select(Issue.id, Issue.status, geom.label("g")).where(
            func.ST_Intersects(Issue.location, envelope)
        )
        if published_only:
            # Explicit publication rule; RLS applies the same rule underneath.
            inner = inner.where(
                Issue.visibility == IssueVisibility.PUBLIC, Issue.status.in_(PUBLISHED_STATUSES)
            )
        inner = self._apply_filters(inner, filters).subquery()
        cell = cell_size_degrees(zoom)
        snapped = func.ST_SnapToGrid(inner.c.g, cell)
        centre = func.ST_Centroid(func.ST_Collect(inner.c.g))
        rows = self.db.execute(
            select(
                func.ST_Y(centre),
                func.ST_X(centre),
                func.count(),
                func.min(cast(inner.c.id, String)),
                func.min(inner.c.status),
            )
            .group_by(snapped)
            .limit(MAX_CLUSTERS)
        ).all()
        clusters = [
            Cluster(
                latitude=lat,
                longitude=lon,
                count=count,
                issue_id=uuid.UUID(first_id) if count == 1 else None,
                status=IssueStatus(status) if count == 1 else None,
            )
            for lat, lon, count, first_id, status in rows
        ]
        return clusters, sum(c.count for c in clusters)

    def nearby_published(
        self,
        latitude: float,
        longitude: float,
        radius_m: int,
        *,
        category_code: str | None,
        limit: int,
    ) -> list[tuple[Issue, float]]:
        here = cast(point(latitude, longitude), Geography)
        distance = func.ST_Distance(Issue.location, here).label("distance")
        stmt = select(Issue, distance).where(
            Issue.visibility == IssueVisibility.PUBLIC,
            Issue.status.in_(PUBLISHED_STATUSES),
            func.ST_DWithin(Issue.location, here, radius_m),
        )
        stmt = self._apply_filters(stmt, MapFilters(category_code=category_code))
        rows = self.db.execute(stmt.order_by(distance).limit(limit)).all()
        return [(issue, float(d)) for issue, d in rows]

    def nearby_for_staff(
        self, access: CouncilAccess, issue_id: uuid.UUID, radius_m: int, limit: int
    ) -> list[tuple[Issue, float]]:
        """Other reports in the same council near this one, any status: for spotting duplicates."""
        access.require(Permission.ISSUES_VIEW)
        issue = self.db.scalar(
            select(Issue).where(Issue.id == issue_id, Issue.council_id == access.council.id)
        )
        if issue is None:
            raise NotFoundError("Report not found.")
        origin = select(Issue.location).where(Issue.id == issue.id).scalar_subquery()
        distance = func.ST_Distance(Issue.location, origin).label("distance")
        rows = self.db.execute(
            select(Issue, distance)
            .where(
                and_(
                    Issue.council_id == access.council.id,
                    Issue.id != issue.id,
                    func.ST_DWithin(Issue.location, origin, radius_m),
                )
            )
            .order_by(distance)
            .limit(limit)
        ).all()
        return [(other, float(d)) for other, d in rows]
