"""Application settings loaded from environment variables.

Secrets are never hardcoded: every sensitive value must come from the
environment (or a secret manager that populates it).
"""

from functools import lru_cache
from typing import Literal

from pydantic import (
    Field,
    PostgresDsn,
    RedisDsn,
    SecretStr,
    field_validator,
    model_validator,
)
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
    # The background worker's connection (role civicwatch_worker): it reads
    # notifications across all users to email them, which the API role cannot.
    worker_database_url: PostgresDsn | None = None
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
    # Council staff and platform admins hold access to other people's data,
    # so their sessions are shorter: a working shift idle, a week at most.
    staff_session_idle_timeout_minutes: int = Field(default=12 * 60, ge=5)
    staff_session_absolute_timeout_minutes: int = Field(default=60 * 24 * 7, ge=5)
    # Avoid a database write on every request: refresh last_seen_at at most this often.
    session_touch_interval_seconds: int = Field(default=300, ge=0)

    # --- Rate limits (fixed windows, enforced in Redis) ----------------------
    login_attempts_per_ip: int = 30
    login_failures_per_account: int = 5
    login_window_seconds: int = 15 * 60
    registrations_per_ip: int = 10
    registration_window_seconds: int = 60 * 60
    reports_per_user: int = 20
    report_window_seconds: int = 60 * 60

    photo_uploads_per_user: int = 60
    photo_upload_window_seconds: int = 60 * 60
    # Public read endpoints that run spatial or aggregate queries (map
    # clusters, nearby, council lookup, statistics, public listing).
    public_reads_per_ip: int = 600
    public_read_window_seconds: int = 5 * 60
    exports_per_user: int = 20
    export_window_seconds: int = 60 * 60

    # --- Request size --------------------------------------------------------------
    # Largest request body accepted; photo uploads and boundary uploads have
    # their own, larger limits (see app/core/middleware.py).
    max_request_bytes: int = Field(default=1024 * 1024, ge=16 * 1024)
    max_boundary_request_bytes: int = Field(default=8 * 1024 * 1024, ge=16 * 1024)

    # --- Photo storage (S3-compatible; MinIO locally) -----------------------------
    # The bucket must be private. Browsers only ever receive short-lived
    # pre-signed URLs, signed for storage_public_endpoint_url.
    storage_endpoint_url: str | None = "http://localhost:9000"
    storage_public_endpoint_url: str | None = None
    storage_region: str = "us-east-1"
    storage_bucket: str = "civicwatch-media"
    storage_access_key_id: SecretStr | None = None
    storage_secret_access_key: SecretStr | None = None
    media_url_ttl_seconds: int = Field(default=300, ge=30, le=3600)

    # --- Photos ------------------------------------------------------------------------
    photo_max_upload_bytes: int = 10 * 1024 * 1024
    photos_per_issue: int = 5
    # Decompression-bomb guard: refuse images with more pixels than this.
    photo_max_pixels: int = 40_000_000
    photo_display_max_px: int = 1600
    photo_thumbnail_max_px: int = 400
    photo_jpeg_quality: int = Field(default=80, ge=50, le=95)

    # --- Email notifications (SMTP) --------------------------------------------------
    # Unset smtp_host disables email delivery; in-app notifications still work.
    smtp_host: str | None = None
    smtp_port: int = 587
    smtp_username: str | None = None
    smtp_password: SecretStr | None = None
    smtp_starttls: bool = True
    smtp_use_ssl: bool = False
    email_from: str | None = None
    # Absolute address of the web app, for links in emails.
    public_web_url: str = "http://localhost:3000"
    email_batch_size: int = Field(default=50, ge=1, le=500)
    email_max_attempts: int = Field(default=5, ge=1, le=20)
    # Older undelivered notifications are not emailed (no floods after an outage).
    email_max_age_hours: int = Field(default=48, ge=1)

    # --- Service area -----------------------------------------------------------
    # Reports must fall inside this box (west, south, east, north; WGS 84).
    # Default: Zimbabwe with a small margin. Council boundaries (Milestone 4)
    # add a precise check per council.
    service_area_bbox: tuple[float, float, float, float] = (25.0, -22.6, 33.2, -15.4)

    @field_validator(
        "storage_endpoint_url",
        "storage_public_endpoint_url",
        "smtp_host",
        "smtp_username",
        "smtp_password",
        "email_from",
        mode="before",
    )
    @classmethod
    def _empty_is_unset(cls, value: object) -> object:
        # Compose passes unset optional variables as empty strings.
        return None if value == "" else value

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
        if self.smtp_host and not self.email_from:
            raise ValueError("email_from must be set when smtp_host is set")
        if self.environment in ("staging", "production"):
            self._check_deployed()
        if (
            self.staff_session_idle_timeout_minutes > self.session_idle_timeout_minutes
            or self.staff_session_absolute_timeout_minutes > self.session_absolute_timeout_minutes
        ):
            raise ValueError("staff session limits must not be longer than resident limits")
        return self

    def _check_deployed(self) -> None:
        """Refuse settings that are only acceptable on a developer's machine."""
        insecure = [o for o in self.cors_origins if not o.startswith("https://")]
        if insecure:
            raise ValueError(f"cors_origins must use https outside development: {insecure}")
        if not self.public_web_url.startswith("https://"):
            raise ValueError("public_web_url must use https outside development")
        if self.storage_access_key_id is None or self.storage_secret_access_key is None:
            raise ValueError("storage credentials must be set outside development")
        if self.migration_database_url is None:
            raise ValueError(
                "migration_database_url must be set: the API must not connect as the schema owner"
            )
        if self.smtp_host and self.worker_database_url is None:
            raise ValueError("worker_database_url must be set when email delivery is enabled")
        if self.smtp_host and not (self.smtp_starttls or self.smtp_use_ssl):
            raise ValueError("SMTP must use STARTTLS or TLS outside development")

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
