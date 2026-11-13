from datetime import datetime

from pydantic import (
    BaseModel,
    ConfigDict,
    EmailStr,
    Field,
    SecretStr,
    field_validator,
    model_validator,
)

from app.schemas.users import UserRead, normalise_full_name

PASSWORD_MIN_LENGTH = 10
# Upper bound stops very long inputs being used to burn CPU in Argon2.
PASSWORD_MAX_LENGTH = 128


def validate_new_password(password: SecretStr) -> SecretStr:
    value = password.get_secret_value()
    if len(value) < PASSWORD_MIN_LENGTH:
        raise ValueError(f"Password must be at least {PASSWORD_MIN_LENGTH} characters.")
    if len(value) > PASSWORD_MAX_LENGTH:
        raise ValueError(f"Password must be at most {PASSWORD_MAX_LENGTH} characters.")
    if not value.strip():
        raise ValueError("Password cannot be only spaces.")
    return password


class RegisterRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    email: EmailStr = Field(max_length=254)
    password: SecretStr
    full_name: str = Field(min_length=1, max_length=120)

    _password = field_validator("password")(validate_new_password)
    _full_name = field_validator("full_name")(normalise_full_name)

    @model_validator(mode="after")
    def _password_differs_from_email(self) -> "RegisterRequest":
        if self.password.get_secret_value().strip().lower() == self.email.lower():
            raise ValueError("Password must not be the same as your email address.")
        return self


class LoginRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    email: EmailStr = Field(max_length=254)
    password: SecretStr = Field(max_length=PASSWORD_MAX_LENGTH)


class ChangePasswordRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    current_password: SecretStr = Field(max_length=PASSWORD_MAX_LENGTH)
    new_password: SecretStr

    _new_password = field_validator("new_password")(validate_new_password)

    @model_validator(mode="after")
    def _new_differs_from_current(self) -> "ChangePasswordRequest":
        if self.new_password.get_secret_value() == self.current_password.get_secret_value():
            raise ValueError("New password must be different from your current password.")
        return self


class SessionResponse(BaseModel):
    """Returned on sign-in and by GET /auth/session.

    `csrf_token` must be sent as the X-CSRF-Token header on every
    state-changing request made with this session.
    """

    user: UserRead
    csrf_token: str
    expires_at: datetime
