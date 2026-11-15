"""Performance figures for council staff, public transparency statistics and CSV exports.

Public statistics count only PUBLIC reports a council has verified (the same
rule as public browsing); the database's RLS policies apply the same rule
underneath. Staff figures cover their own council only.
"""

import csv
import io
import uuid
from dataclasses import dataclass
from datetime import UTC, date, datetime, time, timedelta

from sqlalchemy import ColumnElement, Select, and_, distinct, func, or_, select
from sqlalchemy.orm import Session

from app.core.errors import FieldValidationError
from app.models.councils import Council
from app.models.departments import Department
from app.models.engagement import ResolutionFeedback
from app.models.issues import (
    PUBLISHED_STATUSES,
    Issue,
    IssueAssignment,
    IssueCategory,
    IssueStatus,
    IssueStatusHistory,
    IssueVisibility,
)
from app.permissions.council_access import CouncilAccess
from app.permissions.rbac import Permission
from app.services.audit import record_audit

S = IssueStatus
OPEN_STATUSES = (
    S.SUBMITTED,
    S.UNDER_REVIEW,
    S.NEEDS_INFORMATION,
    S.VERIFIED,
    S.ASSIGNED,
    S.IN_PROGRESS,
)
FIXED_STATUSES = (S.RESOLVED, S.CLOSED)
PUBLIC_OPEN_STATUSES = (S.VERIFIED, S.ASSIGNED, S.IN_PROGRESS)
EXPORT_MAX_ROWS = 10_000
EXPORT_MAX_DAYS = 366
PERIODS = (30, 90, 365)


@dataclass(frozen=True)
class CategoryCount:
    code: str
    name: str
    received: int
    fixed: int


@dataclass(frozen=True)
class DepartmentLoad:
    id: uuid.UUID
    name: str
    assigned: int
    in_progress: int
    oldest_open_days: int | None


@dataclass(frozen=True)
class Performance:
    since: datetime
    received: int
    open_now: int
    awaiting_review: int
    awaiting_assignment: int
    fixed_in_period: int
    median_hours_to_first_response: float | None
    median_hours_to_verify: float | None
    median_hours_to_fix: float | None
    categories: list[CategoryCount]
    departments: list[DepartmentLoad]
    feedback_responses: int
    feedback_fixed: int


@dataclass(frozen=True)
class PublicCouncilStats:
    id: uuid.UUID
    slug: str
    name: str
    published: int
    open: int
    fixed: int
    median_days_to_fix: float | None


@dataclass(frozen=True)
class PublicStats:
    published: int
    open: int
    fixed: int
    median_days_to_fix: float | None
    categories: list[CategoryCount]
    councils: list[PublicCouncilStats]


def _first_reached(*statuses: IssueStatus):
    """When each report first reached any of these statuses."""
    return (
        select(IssueStatusHistory.issue_id, func.min(IssueStatusHistory.created_at).label("at"))
        .where(IssueStatusHistory.to_status.in_(statuses))
        .group_by(IssueStatusHistory.issue_id)
        .subquery()
    )


def _first_response():
    """When staff first acted on each report (its first change after submission)."""
    return (
        select(IssueStatusHistory.issue_id, func.min(IssueStatusHistory.created_at).label("at"))
        .where(IssueStatusHistory.from_status.is_not(None))
        .group_by(IssueStatusHistory.issue_id)
        .subquery()
    )


def _median_seconds(start: ColumnElement, end: ColumnElement) -> ColumnElement:
    return func.percentile_cont(0.5).within_group(func.extract("epoch", end - start))


def _round(value: float | None, divisor: float) -> float | None:
    return None if value is None else round(float(value) / divisor, 1)


def _is_public_published() -> ColumnElement[bool]:
    return and_(Issue.visibility == IssueVisibility.PUBLIC, Issue.status.in_(PUBLISHED_STATUSES))


class AnalyticsService:
    def __init__(self, db: Session) -> None:
        self.db = db

    # --- Council staff -------------------------------------------------------------

    def performance(self, access: CouncilAccess, days: int) -> Performance:
        access.require(Permission.ANALYTICS_VIEW)
        if days not in PERIODS:
            raise FieldValidationError("days", "Choose 30, 90 or 365 days.")
        council_id = access.council.id
        now = datetime.now(UTC)
        since = now - timedelta(days=days)
        in_council = Issue.council_id == council_id
        received_in_period = and_(in_council, Issue.created_at >= since)

        status_counts = dict(
            self.db.execute(
                select(Issue.status, func.count())
                .where(in_council, Issue.status.in_(OPEN_STATUSES))
                .group_by(Issue.status)
            ).all()
        )
        received = self.db.scalar(select(func.count()).where(received_in_period)) or 0

        fixed = _first_reached(*FIXED_STATUSES)
        fixed_in_period = (
            self.db.scalar(
                select(func.count())
                .select_from(fixed)
                .join(Issue, Issue.id == fixed.c.issue_id)
                .where(in_council, fixed.c.at >= since)
            )
            or 0
        )

        def median_hours(reached) -> float | None:
            value = self.db.scalar(
                select(_median_seconds(Issue.created_at, reached.c.at))
                .select_from(reached)
                .join(Issue, Issue.id == reached.c.issue_id)
                .where(received_in_period)
            )
            return _round(value, 3600)

        categories = [
            CategoryCount(code, name, received_count, fixed_count)
            for code, name, received_count, fixed_count in self.db.execute(
                select(
                    IssueCategory.code,
                    IssueCategory.name,
                    func.count(Issue.id),
                    func.count(Issue.id).filter(Issue.status.in_(FIXED_STATUSES)),
                )
                .join(Issue, Issue.category_id == IssueCategory.id)
                .where(received_in_period)
                .group_by(IssueCategory.id)
                .order_by(func.count(Issue.id).desc(), IssueCategory.sort_order)
            ).all()
        ]

        active = and_(
            IssueAssignment.ended_at.is_(None),
            IssueAssignment.issue_id == Issue.id,
            Issue.status.in_((S.ASSIGNED, S.IN_PROGRESS)),
        )
        departments = [
            DepartmentLoad(
                dept_id,
                name,
                assigned,
                in_progress,
                None if oldest is None else (now - oldest).days,
            )
            for dept_id, name, assigned, in_progress, oldest in self.db.execute(
                select(
                    Department.id,
                    Department.name,
                    func.count(Issue.id).filter(Issue.status == S.ASSIGNED),
                    func.count(Issue.id).filter(Issue.status == S.IN_PROGRESS),
                    func.min(Issue.created_at),
                )
                .outerjoin(
                    IssueAssignment,
                    and_(
                        IssueAssignment.department_id == Department.id,
                        IssueAssignment.ended_at.is_(None),
                    ),
                )
                .outerjoin(Issue, active)
                .where(
                    Department.council_id == council_id,
                    or_(Department.is_active.is_(True), Issue.id.is_not(None)),
                )
                .group_by(Department.id)
                .order_by(func.count(Issue.id).desc(), Department.name)
            ).all()
        ]

        feedback_responses, feedback_fixed = self.db.execute(
            select(
                func.count(),
                func.count().filter(ResolutionFeedback.fixed.is_(True)),
            ).where(
                ResolutionFeedback.council_id == council_id,
                ResolutionFeedback.created_at >= since,
            )
        ).one()

        return Performance(
            since=since,
            received=received,
            open_now=sum(status_counts.values()),
            awaiting_review=status_counts.get(S.SUBMITTED, 0)
            + status_counts.get(S.UNDER_REVIEW, 0),
            awaiting_assignment=status_counts.get(S.VERIFIED, 0),
            fixed_in_period=fixed_in_period,
            median_hours_to_first_response=median_hours(_first_response()),
            median_hours_to_verify=median_hours(_first_reached(S.VERIFIED)),
            median_hours_to_fix=median_hours(fixed),
            categories=categories,
            departments=departments,
            feedback_responses=feedback_responses,
            feedback_fixed=feedback_fixed,
        )

    # --- Public -----------------------------------------------------------------------

    def public_stats(self, council_id: uuid.UUID | None = None) -> PublicStats:
        """Statistics about published public reports only; never private or unverified ones."""
        published = _is_public_published()
        scope: list[ColumnElement[bool]] = [published, Council.is_active.is_(True)]
        if council_id is not None:
            scope.append(Issue.council_id == council_id)

        def base(stmt: Select) -> Select:
            return stmt.join(Council, Council.id == Issue.council_id).where(*scope)

        is_open = Issue.status.in_(PUBLIC_OPEN_STATUSES)
        is_fixed = Issue.status.in_(FIXED_STATUSES)
        verified = _first_reached(S.VERIFIED)
        fixed = _first_reached(*FIXED_STATUSES)
        days_to_fix = _median_seconds(verified.c.at, fixed.c.at)

        def with_fix_times(stmt: Select) -> Select:
            return stmt.outerjoin(verified, verified.c.issue_id == Issue.id).outerjoin(
                fixed, fixed.c.issue_id == Issue.id
            )

        totals = self.db.execute(
            base(
                with_fix_times(
                    select(
                        func.count(distinct(Issue.id)),
                        func.count(distinct(Issue.id)).filter(is_open),
                        func.count(distinct(Issue.id)).filter(is_fixed),
                        days_to_fix.filter(is_fixed),
                    ).select_from(Issue)
                )
            )
        ).one()

        categories = [
            CategoryCount(code, name, count, fixed_count)
            for code, name, count, fixed_count in self.db.execute(
                base(
                    select(
                        IssueCategory.code,
                        IssueCategory.name,
                        func.count(Issue.id),
                        func.count(Issue.id).filter(is_fixed),
                    )
                    .select_from(Issue)
                    .join(IssueCategory, IssueCategory.id == Issue.category_id)
                )
                .group_by(IssueCategory.id)
                .order_by(func.count(Issue.id).desc(), IssueCategory.sort_order)
            ).all()
        ]

        councils = [
            PublicCouncilStats(
                cid, slug, name, count, open_count, fixed_count, _round(median, 86400)
            )
            for cid, slug, name, count, open_count, fixed_count, median in self.db.execute(
                base(
                    with_fix_times(
                        select(
                            Council.id,
                            Council.slug,
                            Council.name,
                            func.count(Issue.id),
                            func.count(Issue.id).filter(is_open),
                            func.count(Issue.id).filter(is_fixed),
                            days_to_fix.filter(is_fixed),
                        ).select_from(Issue)
                    )
                )
                .group_by(Council.id)
                .order_by(func.count(Issue.id).desc(), Council.name)
            ).all()
        ]
        count, open_count, fixed_count, median = totals
        return PublicStats(
            published=count,
            open=open_count,
            fixed=fixed_count,
            median_days_to_fix=_round(median, 86400),
            categories=categories,
            councils=councils,
        )

    # --- Export ------------------------------------------------------------------------

    def export_csv(self, access: CouncilAccess, start: date, end: date) -> tuple[str, int]:
        """Reports received between two dates (inclusive) as CSV. No reporter details."""
        access.require(Permission.REPORTS_EXPORT)
        if end < start:
            raise FieldValidationError("to", "The end date must not be before the start date.")
        if (end - start).days >= EXPORT_MAX_DAYS:
            raise FieldValidationError("to", "Export at most one year at a time.")
        start_at = datetime.combine(start, time.min, tzinfo=UTC)
        end_at = datetime.combine(end + timedelta(days=1), time.min, tzinfo=UTC)

        verified = _first_reached(S.VERIFIED)
        fixed = _first_reached(*FIXED_STATUSES)
        stmt = (
            select(
                Issue.reference_number,
                Issue.created_at,
                IssueCategory.name,
                Issue.status,
                Issue.visibility,
                Issue.title,
                Issue.location_description,
                Issue.latitude,
                Issue.longitude,
                Department.name,
                verified.c.at,
                fixed.c.at,
            )
            .join(IssueCategory, IssueCategory.id == Issue.category_id)
            .outerjoin(
                IssueAssignment,
                and_(IssueAssignment.issue_id == Issue.id, IssueAssignment.ended_at.is_(None)),
            )
            .outerjoin(Department, Department.id == IssueAssignment.department_id)
            .outerjoin(verified, verified.c.issue_id == Issue.id)
            .outerjoin(fixed, fixed.c.issue_id == Issue.id)
            .where(
                Issue.council_id == access.council.id,
                Issue.created_at >= start_at,
                Issue.created_at < end_at,
            )
            .order_by(Issue.reference_number)
            .limit(EXPORT_MAX_ROWS + 1)
        )
        rows = self.db.execute(stmt).all()
        if len(rows) > EXPORT_MAX_ROWS:
            raise FieldValidationError(
                "to", f"More than {EXPORT_MAX_ROWS:,} reports in this period; choose a shorter one."
            )

        buffer = io.StringIO()
        writer = csv.writer(buffer, lineterminator="\r\n")
        writer.writerow(
            [
                "reference",
                "received_at_utc",
                "category",
                "status",
                "visibility",
                "title",
                "location_description",
                "latitude",
                "longitude",
                "department",
                "verified_at_utc",
                "fixed_at_utc",
            ]
        )
        for (
            number,
            created_at,
            category,
            status,
            visibility,
            title,
            place,
            lat,
            lon,
            department,
            verified_at,
            fixed_at,
        ) in rows:
            writer.writerow(
                [
                    f"CW-{number:06d}",
                    _iso(created_at),
                    category,
                    IssueStatus(status).value,
                    IssueVisibility(visibility).value,
                    safe_cell(title),
                    safe_cell(place),
                    f"{lat:.6f}",
                    f"{lon:.6f}",
                    safe_cell(department),
                    _iso(verified_at),
                    _iso(fixed_at),
                ]
            )
        record_audit(
            self.db,
            action="reports.exported",
            actor_user_id=access.user.id,
            council_id=access.council.id,
            target_type="council",
            target_id=access.council.id,
            details={"from": start.isoformat(), "to": end.isoformat(), "rows": len(rows)},
        )
        self.db.commit()
        return buffer.getvalue(), len(rows)


def _iso(value: datetime | None) -> str:
    return "" if value is None else value.astimezone(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


_FORMULA_PREFIXES = ("=", "+", "-", "@", "\t", "\r")


def safe_cell(value: str | None) -> str:
    """Stop spreadsheet programs treating resident-written text as a formula."""
    if not value:
        return ""
    return "'" + value if value.startswith(_FORMULA_PREFIXES) else value
