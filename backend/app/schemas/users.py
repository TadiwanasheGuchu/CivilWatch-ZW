import re
import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator

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
    created_at: datetime


class UpdateProfileRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    full_name: str = Field(min_length=1, max_length=120)

    _normalise = field_validator("full_name")(normalise_full_name)
