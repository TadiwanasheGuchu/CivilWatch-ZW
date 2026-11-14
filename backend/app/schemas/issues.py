import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.models.issues import IssueStatus, IssueVisibility
from app.schemas.councils import CouncilSummary

_CONTROL_CHARS = {chr(c) for c in range(32)} - {"\n", "\t"} | {"\x7f"}


def _clean_text(value: str) -> str:
    if any(ch in _CONTROL_CHARS for ch in value):
        raise ValueError("Text contains characters that are not allowed.")
    return value.strip()


class CategoryRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    code: str
    name: str
    description: str


class CreateIssueRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    # The resident chooses which council to report to (product decision). This
    # only selects the recipient; it never grants the reporter any council access.
    council_id: uuid.UUID
    category_id: uuid.UUID
    title: str = Field(min_length=5, max_length=120)
    description: str = Field(min_length=10, max_length=2000)
    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)
    location_description: str | None = Field(default=None, max_length=200)
    visibility: IssueVisibility

    @field_validator("title", "description")
    @classmethod
    def _text(cls, value: str) -> str:
        value = _clean_text(value)
        return value

    @field_validator("title")
    @classmethod
    def _title_single_line(cls, value: str) -> str:
        value = " ".join(value.split())
        if len(value) < 5:
            raise ValueError("Give the problem a short title of at least 5 characters.")
        return value

    @field_validator("description")
    @classmethod
    def _description_length(cls, value: str) -> str:
        if len(value) < 10:
            raise ValueError("Describe the problem in at least 10 characters.")
        return value

    @field_validator("location_description")
    @classmethod
    def _location_description(cls, value: str | None) -> str | None:
        if value is None:
            return None
        value = " ".join(_clean_text(value).split())
        return value or None


class CategorySummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    code: str
    name: str


class PhotoRead(BaseModel):
    """URLs are pre-signed and expire after a few minutes; fetch the report again for fresh ones."""

    id: uuid.UUID
    url: str
    thumbnail_url: str
    width: int
    height: int


class PublicIssue(BaseModel):
    """What anyone may see of a published PUBLIC report. Never identifies the reporter."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    reference: str
    council: CouncilSummary
    category: CategorySummary
    title: str
    description: str
    status: IssueStatus
    latitude: float
    longitude: float
    location_description: str | None
    created_at: datetime
    updated_at: datetime
    photo_count: int = 0
    cover_thumbnail_url: str | None = None


class OwnIssue(PublicIssue):
    """The reporter's own view of their report, including private ones."""

    visibility: IssueVisibility
    is_published: bool


class StatusChange(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    from_status: IssueStatus | None
    to_status: IssueStatus
    created_at: datetime


class OwnStatusChange(StatusChange):
    """The reporter also sees the council's messages to them."""

    note: str | None = None


class OwnIssueDetail(OwnIssue):
    history: list[OwnStatusChange]
    photos: list[PhotoRead]


class PublicIssueDetail(PublicIssue):
    history: list[StatusChange]
    photos: list[PhotoRead]
