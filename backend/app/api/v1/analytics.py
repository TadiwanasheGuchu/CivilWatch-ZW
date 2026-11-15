"""Performance figures (council staff), public statistics, and CSV exports."""

import dataclasses
import uuid
from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, Query, Response

from app.api.deps import (
    CouncilAccessDep,
    DbDep,
    PublicReadLimit,
    SettingsDep,
    get_rate_limiter,
)
from app.core.rate_limit import RateLimiter
from app.schemas.analytics import PerformanceRead, PublicStatsRead
from app.services.analytics import AnalyticsService

router = APIRouter(tags=["analytics"])
_STAFF_ERRORS = {
    401: {"description": "Not signed in"},
    403: {"description": "Not staff of this council or missing permission"},
    404: {"description": "Council not found"},
}


@router.get(
    "/analytics/public",
    dependencies=[PublicReadLimit],
    response_model=PublicStatsRead,
    summary="Public statistics about verified public reports",
)
def public_statistics(
    db: DbDep, response: Response, council_id: Annotated[uuid.UUID | None, Query()] = None
) -> PublicStatsRead:
    # Anyone may read these, signed in or not; they never include private reports.
    response.headers["Cache-Control"] = "public, max-age=300"
    stats = AnalyticsService(db).public_stats(council_id)
    return PublicStatsRead.model_validate(stats)


@router.get(
    "/councils/{council_id}/analytics/performance",
    response_model=PerformanceRead,
    summary="The council's performance over a period",
    responses=_STAFF_ERRORS,
)
def council_performance(
    access: CouncilAccessDep,
    db: DbDep,
    days: Annotated[int, Query(description="One of 30, 90 or 365")] = 90,
) -> PerformanceRead:
    result = AnalyticsService(db).performance(access, days)
    return PerformanceRead(period_days=days, **dataclasses.asdict(result))


@router.get(
    "/councils/{council_id}/reports/export",
    summary="Reports received between two dates, as CSV",
    response_class=Response,
    responses={
        **_STAFF_ERRORS,
        200: {"content": {"text/csv": {}}, "description": "CSV file"},
        422: {"description": "Bad dates, over a year, or more than 10,000 reports"},
    },
)
def export_reports(
    access: CouncilAccessDep,
    db: DbDep,
    settings: SettingsDep,
    limiter: Annotated[RateLimiter, Depends(get_rate_limiter)],
    start: Annotated[date, Query(alias="from")],
    end: Annotated[date, Query(alias="to")],
) -> Response:
    limiter.hit(
        "export:user",
        str(access.user.id),
        limit=settings.exports_per_user,
        window_seconds=settings.export_window_seconds,
    )
    body, _ = AnalyticsService(db).export_csv(access, start, end)
    filename = f"civicwatch-{access.council.slug}-{start.isoformat()}-to-{end.isoformat()}.csv"
    return Response(
        # A byte-order mark so spreadsheet programs read UTF-8 correctly.
        content="﻿" + body,
        media_type="text/csv; charset=utf-8",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            "Cache-Control": "no-store",
        },
    )
