import re
import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

_CONTROL_CHARS = re.compile(r"[\x00-\x1f\x7f]")


def normalise_full_name(value: str) -> str:
    value = " ".join(value.split())
    if not value:
        raise ValueError("Enter your full name.")
    if _CONTROL_CHARS.search(value):
        raise ValueError("Name contains characters that are not allowed.")
    return value


class UserRead(BaseModel):
    """The signed-in user's own profile. Never used for other users."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    email: str
    full_name: str
    is_platform_admin: bool
    email_notifications: bool = True
    created_at: datetime


class UpdateProfileRequest(BaseModel):
    """Send `full_name`, `email_notifications`, or both."""

    model_config = ConfigDict(extra="forbid")

    full_name: str | None = Field(default=None, min_length=1, max_length=120)
    email_notifications: bool | None = None

    _normalise = field_validator("full_name")(
        lambda value: None if value is None else normalise_full_name(value)
    )

    @model_validator(mode="after")
    def _something(self) -> "UpdateProfileRequest":
        if self.full_name is None and self.email_notifications is None:
            raise ValueError("Send a name or an email preference to change.")
        return self
