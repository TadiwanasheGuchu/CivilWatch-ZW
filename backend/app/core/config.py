"""Application settings loaded from environment variables.

Secrets are never hardcoded: every sensitive value must come from the
environment (or a secret manager that populates it).
"""

from functools import lru_cache
from typing import Literal

from pydantic import Field, PostgresDsn, RedisDsn, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="CIVICWATCH_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    environment: Literal["development", "test", "staging", "production"] = "development"
    app_name: str = "CivicWatch ZW API"
    api_v1_prefix: str = "/api/v1"
    log_level: str = "INFO"

    database_url: PostgresDsn = Field(
        default=PostgresDsn("postgresql+psycopg://civicwatch:civicwatch@localhost:5432/civicwatch")
    )
    # Schema-owner connection used only by Alembic. The API's database_url
    # must use the unprivileged `civicwatch_app` role so RLS applies to it.
    migration_database_url: PostgresDsn | None = None
    database_pool_size: int = Field(default=5, ge=1, le=50)
    database_max_overflow: int = Field(default=10, ge=0, le=100)

    redis_url: RedisDsn = Field(default=RedisDsn("redis://localhost:6379/0"))

    # Origins allowed to call the API from a browser (the Next.js frontend).
    cors_origins: list[str] = Field(default_factory=lambda: ["http://localhost:3000"])

    # --- Sessions (see docs/06-security-and-privacy.md) ---------------------
    # The __Host- prefix makes browsers reject the cookie unless it is Secure,
    # host-only and Path=/. Local HTTP development overrides name and flag.
    session_cookie_name: str = "__Host-cw_session"
    session_cookie_secure: bool = True
    session_idle_timeout_minutes: int = Field(default=60 * 24 * 7, ge=5)
    session_absolute_timeout_minutes: int = Field(default=60 * 24 * 30, ge=5)
    # Avoid a database write on every request: refresh last_seen_at at most this often.
    session_touch_interval_seconds: int = Field(default=300, ge=0)

    # --- Rate limits (fixed windows, enforced in Redis) ----------------------
    login_attempts_per_ip: int = 30
    login_failures_per_account: int = 5
    login_window_seconds: int = 15 * 60
    registrations_per_ip: int = 10
    registration_window_seconds: int = 60 * 60

    @field_validator("cors_origins", mode="before")
    @classmethod
    def _split_origins(cls, value: object) -> object:
        if isinstance(value, str) and not value.startswith("["):
            return [origin.strip() for origin in value.split(",") if origin.strip()]
        return value

    @model_validator(mode="after")
    def _production_requires_secure_cookies(self) -> "Settings":
        if self.environment in ("staging", "production") and not self.session_cookie_secure:
            raise ValueError("session_cookie_secure must be true outside development and test")
        if self.session_cookie_name.startswith("__Host-") and not self.session_cookie_secure:
            raise ValueError("__Host- cookies require session_cookie_secure=true")
        if self.session_absolute_timeout_minutes < self.session_idle_timeout_minutes:
            raise ValueError("absolute session timeout must not be shorter than idle timeout")
        return self

    @property
    def effective_migration_database_url(self) -> str:
        return str(self.migration_database_url or self.database_url)

    @property
    def is_production(self) -> bool:
        return self.environment == "production"

    @property
    def docs_enabled(self) -> bool:
        # OpenAPI docs stay available outside production; production exposes
        # the schema only through the authenticated developer portal later.
        return not self.is_production


@lru_cache
def get_settings() -> Settings:
    return Settings()
