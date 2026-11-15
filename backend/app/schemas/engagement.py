import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.models.engagement import NotificationKind
from app.schemas.operations import clean_note


class NotificationRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    kind: NotificationKind
    title: str
    body: str | None
    link: str
    created_at: datetime
    read_at: datetime | None


class UnreadCount(BaseModel):
    unread: int


class FeedbackRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    fixed: bool
    comment: str | None = Field(default=None, max_length=1000)

    _comment = field_validator("comment")(clean_note)


class FeedbackRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    fixed: bool
    comment: str | None
    created_at: datetime
