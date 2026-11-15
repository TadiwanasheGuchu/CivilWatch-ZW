"""Response schemas for performance figures and public statistics."""

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class _Read(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class CategoryCountRead(_Read):
    code: str
    name: str
    received: int
    fixed: int


class DepartmentLoadRead(_Read):
    id: uuid.UUID
    name: str
    assigned: int
    in_progress: int
    oldest_open_days: int | None


class PerformanceRead(_Read):
    """A council's figures. Times are medians over reports received in the period."""

    period_days: int
    since: datetime
    received: int
    open_now: int
    awaiting_review: int
    awaiting_assignment: int
    fixed_in_period: int
    median_hours_to_first_response: float | None
    median_hours_to_verify: float | None
    median_hours_to_fix: float | None
    categories: list[CategoryCountRead]
    departments: list[DepartmentLoadRead]
    feedback_responses: int
    feedback_fixed: int


class PublicCouncilStatsRead(_Read):
    id: uuid.UUID
    slug: str
    name: str
    published: int
    open: int
    fixed: int
    median_days_to_fix: float | None


class PublicStatsRead(_Read):
    """Counts of verified public reports only; `received` in categories means published."""

    published: int
    open: int
    fixed: int
    median_days_to_fix: float | None
    categories: list[CategoryCountRead]
    councils: list[PublicCouncilStatsRead]
