"""Schemas for council staff working on reports. Never used for residents or the public."""

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.models.issues import IssueStatus, IssueVisibility
from app.schemas.issues import CategorySummary, PhotoRead

_CONTROL = {chr(c) for c in range(32)} - {"\n", "\t"} | {"\x7f"}


def clean_note(value: str | None) -> str | None:
    if value is None:
        return None
    if any(ch in _CONTROL for ch in value):
        raise ValueError("Text contains characters that are not allowed.")
    value = value.strip()
    return value or None


def clean_department_name(value: str | None) -> str | None:
    if value is None:
        return None
    value = " ".join((clean_note(value) or "").split())
    if len(value) < 2:
        raise ValueError("Give the department a name of at least 2 characters.")
    return value


class DepartmentRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    description: str | None
    is_active: bool


class DepartmentRef(BaseModel):
    id: uuid.UUID
    name: str


class CreateDepartmentRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=2, max_length=80)
    description: str | None = Field(default=None, max_length=240)

    _name = field_validator("name")(clean_department_name)
    _description = field_validator("description")(clean_note)


class UpdateDepartmentRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str | None = Field(default=None, min_length=2, max_length=80)
    description: str | None = Field(default=None, max_length=240)
    is_active: bool | None = None

    _name = field_validator("name")(clean_department_name)
    _description = field_validator("description")(clean_note)


class PersonRef(BaseModel):
    id: uuid.UUID
    full_name: str


class AssignmentRead(BaseModel):
    department: DepartmentRef
    assignee: PersonRef | None
    assigned_at: datetime


class StaffIssueSummary(BaseModel):
    id: uuid.UUID
    reference: str
    title: str
    category: CategorySummary
    status: IssueStatus
    visibility: IssueVisibility
    location_description: str | None
    latitude: float
    longitude: float
    created_at: datetime
    updated_at: datetime
    photo_count: int
    cover_thumbnail_url: str | None
    assignment: AssignmentRead | None


class StaffStatusChange(BaseModel):
    from_status: IssueStatus | None
    to_status: IssueStatus
    note: str | None
    changed_by: str | None
    created_at: datetime


class InternalUpdateRead(BaseModel):
    id: uuid.UUID
    body: str
    author: str | None
    created_at: datetime


class AvailableTransition(BaseModel):
    to_status: IssueStatus
    label: str
    note_required: bool
    needs_duplicate_of: bool


class IssueRef(BaseModel):
    id: uuid.UUID
    reference: str


class StaffIssueDetail(StaffIssueSummary):
    description: str
    # Name only: staff contact reporters through "needs information", so
    # email addresses and other contact details are never shown.
    reporter_name: str
    duplicate_of: IssueRef | None
    photos: list[PhotoRead]
    repair_photos: list[PhotoRead]
    history: list[StaffStatusChange]
    updates: list[InternalUpdateRead]
    available_transitions: list[AvailableTransition]
    can_assign: bool
    can_add_repair_photos: bool
    # The reporter's answer to "Was it fixed?", if given.
    feedback: "FeedbackSummary | None" = None


class FeedbackSummary(BaseModel):
    fixed: bool
    comment: str | None
    created_at: datetime


class TransitionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    to_status: IssueStatus
    note: str | None = Field(default=None, max_length=1000)
    # The report this one duplicates, by reference (CW-000123).
    duplicate_of_reference: str | None = Field(default=None, pattern=r"^CW-\d{1,12}$")

    _note = field_validator("note")(clean_note)


class AssignRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    department_id: uuid.UUID
    assignee_user_id: uuid.UUID | None = None
    note: str | None = Field(default=None, max_length=1000)

    _note = field_validator("note")(clean_note)


class InternalUpdateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    body: str = Field(min_length=1, max_length=2000)

    @field_validator("body")
    @classmethod
    def _body(cls, value: str) -> str:
        cleaned = clean_note(value)
        if not cleaned:
            raise ValueError("Write a note.")
        return cleaned


class StatusCount(BaseModel):
    status: IssueStatus
    count: int


class QueueSummary(BaseModel):
    counts: list[StatusCount]
    assigned_to_me: int


class InformationResponse(BaseModel):
    """The reporter's answer to a request for more information."""

    model_config = ConfigDict(extra="forbid")

    note: str = Field(min_length=1, max_length=1000)

    @field_validator("note")
    @classmethod
    def _note(cls, value: str) -> str:
        cleaned = clean_note(value)
        if not cleaned:
            raise ValueError("Write your answer for the council.")
        return cleaned
