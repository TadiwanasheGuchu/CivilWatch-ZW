"""Report submission and reading, for residents and the public.

Council-side handling (review, verification, assignment) arrives in
Milestone 3 together with the status-transition rules.
"""

import logging
import uuid
from dataclasses import dataclass

from geoalchemy2.elements import WKTElement
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.core.errors import AppError, FieldValidationError, NotFoundError
from app.core.rate_limit import RateLimiter
from app.models.councils import Council
from app.models.identity import User
from app.models.issues import (
    Issue,
    IssueCategory,
    IssueStatus,
    IssueStatusHistory,
)
from app.repositories.issues import CategoryRepository, IssueRepository
from app.schemas.issues import CreateIssueRequest
from app.schemas.pagination import PageParams
from app.services.notifications import Notifier

logger = logging.getLogger(__name__)


class ReportNotAwaitingInformationError(AppError):
    status_code = 409
    code = "not_awaiting_information"


@dataclass(frozen=True)
class IssueView:
    """A report plus how the viewer may see it."""

    issue: Issue
    history: list[IssueStatusHistory]
    viewer_is_reporter: bool


class IssueService:
    def __init__(self, db: Session, settings: Settings, limiter: RateLimiter | None = None) -> None:
        self.db = db
        self.settings = settings
        self.limiter = limiter
        self.issues = IssueRepository(db)
        self.categories = CategoryRepository(db)

    def list_categories(self) -> list[IssueCategory]:
        return self.categories.list_active()

    def submit(self, reporter: User, request: CreateIssueRequest) -> Issue:
        if self.limiter is not None:
            self.limiter.hit(
                "report:user",
                str(reporter.id),
                limit=self.settings.reports_per_user,
                window_seconds=self.settings.report_window_seconds,
            )
        council = self.db.get(Council, request.council_id)
        if council is None or not council.is_active:
            raise FieldValidationError("council_id", "Choose a council from the list.")
        category = self.categories.get_active(request.category_id)
        if category is None:
            raise FieldValidationError("category_id", "Choose a category from the list.")
        self._check_location(council, request.latitude, request.longitude)

        issue = Issue(
            council_id=council.id,
            reporter_id=reporter.id,
            category_id=category.id,
            title=request.title,
            description=request.description,
            status=IssueStatus.SUBMITTED,
            visibility=request.visibility,
            location=WKTElement(f"POINT({request.longitude} {request.latitude})", srid=4326),
            location_description=request.location_description,
        )
        self.issues.add(issue)
        self.issues.add_history(
            IssueStatusHistory(
                issue_id=issue.id,
                from_status=None,
                to_status=IssueStatus.SUBMITTED,
                changed_by_user_id=reporter.id,
            )
        )
        self.db.commit()
        logger.info("report submitted", extra={"issue_id": str(issue.id)})
        return issue

    def list_mine(self, reporter: User, page: PageParams) -> tuple[list[Issue], int]:
        return self.issues.list_for_reporter(reporter.id, offset=page.offset, limit=page.page_size)

    def list_published(
        self,
        page: PageParams,
        *,
        council_id: uuid.UUID | None = None,
        category_code: str | None = None,
        status: IssueStatus | None = None,
    ) -> tuple[list[Issue], int]:
        return self.issues.list_published(
            council_id=council_id,
            category_code=category_code,
            status=status,
            offset=page.offset,
            limit=page.page_size,
        )

    def get_for_viewer(self, issue_id: uuid.UUID, viewer: User | None) -> IssueView:
        """A report the viewer may see as its reporter or as a member of the public.

        Anything else — including another resident's private or unpublished
        report — is reported as not found, so its existence is not revealed.
        Council staff views arrive with Milestone 3.
        """
        issue = self.issues.get(issue_id)
        is_reporter = issue is not None and viewer is not None and issue.reporter_id == viewer.id
        if issue is None or not (is_reporter or issue.is_published):
            raise NotFoundError("Report not found.")
        return IssueView(
            issue=issue, history=self.issues.history(issue.id), viewer_is_reporter=is_reporter
        )

    def respond_with_information(self, reporter: User, issue_id: uuid.UUID, note: str) -> Issue:
        """The reporter answers the council's request; the report returns to review."""
        issue = self.issues.get(issue_id)
        if issue is None or issue.reporter_id != reporter.id:
            raise NotFoundError("Report not found.")
        not_waiting = ReportNotAwaitingInformationError(
            "The council is not waiting for information on this report."
        )
        if issue.status != IssueStatus.NEEDS_INFORMATION:
            raise not_waiting
        # Lock, then re-check: staff may have moved the report meanwhile. RLS
        # only lets the reporter lock it while information is requested.
        locked = self.db.scalar(select(Issue.id).where(Issue.id == issue_id).with_for_update())
        if locked is None:
            raise not_waiting
        self.db.refresh(issue)
        if issue.status != IssueStatus.NEEDS_INFORMATION:
            raise not_waiting
        self.issues.add_history(
            IssueStatusHistory(
                issue_id=issue.id,
                from_status=issue.status,
                to_status=IssueStatus.UNDER_REVIEW,
                changed_by_user_id=reporter.id,
                note=note,
            )
        )
        issue.status = IssueStatus.UNDER_REVIEW
        Notifier(self.db).information_provided(issue, note)
        self.db.commit()
        logger.info("reporter provided information", extra={"issue_id": str(issue.id)})
        return issue

    def _check_location(self, council: Council, latitude: float, longitude: float) -> None:
        west, south, east, north = self.settings.service_area_bbox
        if not (west <= longitude <= east and south <= latitude <= north):
            raise FieldValidationError(
                "latitude", "This location is outside the area CivicWatch currently serves."
            )
        if council.boundary is not None:
            point = func.ST_SetSRID(func.ST_MakePoint(longitude, latitude), 4326)
            inside = self.db.scalar(
                select(func.ST_Covers(Council.boundary, point)).where(Council.id == council.id)
            )
            if not inside:
                raise FieldValidationError(
                    "latitude", f"This location is outside {council.name}'s area."
                )
