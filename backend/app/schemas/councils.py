import re
import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator, model_validator

from app.models.councils import CouncilRole
from app.permissions.rbac import Permission
from app.schemas.users import normalise_full_name

_SLUG = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")


class CouncilSummary(BaseModel):
    """Public directory entry. Contains nothing private."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    slug: str
    name: str


class CreateCouncilRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    slug: str = Field(min_length=3, max_length=60)
    name: str = Field(min_length=1, max_length=160)

    @field_validator("slug")
    @classmethod
    def _slug(cls, value: str) -> str:
        value = value.strip().lower()
        if not _SLUG.match(value):
            raise ValueError("Use lowercase letters, numbers and single hyphens, e.g. 'harare'.")
        return value

    _name = field_validator("name")(normalise_full_name)


class WorkspaceResponse(BaseModel):
    """What the caller may do in a council. Informational for the UI only."""

    council: CouncilSummary
    role: CouncilRole | None
    via_platform_admin: bool
    permissions: list[Permission]


class MembershipRead(BaseModel):
    """A user's own membership (used for the workspace switcher)."""

    id: uuid.UUID
    council: CouncilSummary
    role: CouncilRole
    created_at: datetime


class MemberRead(BaseModel):
    """A council staff member, as seen by other staff of the same council."""

    membership_id: uuid.UUID
    user_id: uuid.UUID
    full_name: str
    email: str
    role: CouncilRole
    department: "DepartmentSummary | None" = None
    granted_at: datetime


class DepartmentSummary(BaseModel):
    id: uuid.UUID
    name: str


class AddMemberRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    email: EmailStr = Field(max_length=254)
    role: CouncilRole


class UpdateMemberRequest(BaseModel):
    """Send `role`, `department_id`, or both. `department_id: null` removes the department."""

    model_config = ConfigDict(extra="forbid")

    role: CouncilRole | None = None
    department_id: uuid.UUID | None = None

    @model_validator(mode="after")
    def _something_to_change(self) -> "UpdateMemberRequest":
        if not self.model_fields_set & {"role", "department_id"}:
            raise ValueError("Send a role or a department to change.")
        if "role" in self.model_fields_set and self.role is None:
            raise ValueError("Role cannot be empty.")
        return self


class AuditLogRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    occurred_at: datetime
    actor_user_id: uuid.UUID | None
    # Display name at read time; None for system and command-line actions.
    actor_name: str | None = None
    action: str
    target_type: str | None
    target_id: uuid.UUID | None
    details: dict
    request_id: str | None
