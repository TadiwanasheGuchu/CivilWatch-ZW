"""Shared request dependencies: services, current session, CSRF."""

import uuid
from typing import Annotated

from fastapi import Depends, Request
from redis import Redis
from sqlalchemy.orm import Session

from app.core.cache import get_redis
from app.core.config import Settings, get_settings
from app.core.database import bind_rls_user, get_db
from app.core.errors import AuthenticationError, PermissionDeniedError
from app.core.rate_limit import RateLimiter
from app.core.security import tokens_match
from app.models.identity import User, UserSession
from app.permissions.council_access import CouncilAccess, resolve_council_access
from app.services.auth import AuthService, ClientContext

CSRF_HEADER = "X-CSRF-Token"
SAFE_METHODS = frozenset({"GET", "HEAD", "OPTIONS"})

SettingsDep = Annotated[Settings, Depends(get_settings)]
DbDep = Annotated[Session, Depends(get_db)]


class CsrfError(PermissionDeniedError):
    code = "csrf_token_invalid"


def get_rate_limiter(redis_client: Annotated[Redis, Depends(get_redis)]) -> RateLimiter:
    return RateLimiter(redis_client)


def get_auth_service(
    db: Annotated[Session, Depends(get_db)],
    limiter: Annotated[RateLimiter, Depends(get_rate_limiter)],
    settings: SettingsDep,
) -> AuthService:
    return AuthService(db, limiter, settings)


AuthServiceDep = Annotated[AuthService, Depends(get_auth_service)]


def get_client_context(request: Request) -> ClientContext:
    # Behind a reverse proxy, run uvicorn with --proxy-headers and a strict
    # --forwarded-allow-ips so request.client reflects the real client.
    host = request.client.host if request.client else "unknown"
    return ClientContext(ip_address=host, user_agent=request.headers.get("User-Agent"))


ClientContextDep = Annotated[ClientContext, Depends(get_client_context)]


def public_read_limit(
    client: ClientContextDep,
    limiter: Annotated[RateLimiter, Depends(get_rate_limiter)],
    settings: SettingsDep,
) -> None:
    """Per-IP limit for public endpoints that run spatial or aggregate queries."""
    limiter.hit(
        "public_read:ip",
        client.ip_address,
        limit=settings.public_reads_per_ip,
        window_seconds=settings.public_read_window_seconds,
    )


PublicReadLimit = Depends(public_read_limit)


def get_session_token(request: Request, settings: SettingsDep) -> str | None:
    return request.cookies.get(settings.session_cookie_name) or None


def get_current_session(
    token: Annotated[str | None, Depends(get_session_token)], service: AuthServiceDep
) -> UserSession:
    session = service.resolve_session(token) if token else None
    if session is None:
        raise AuthenticationError("Please sign in to continue.")
    # From here on, every transaction in this request runs as this user for RLS.
    bind_rls_user(service.db, session.user_id)
    return session


def get_optional_user(
    token: Annotated[str | None, Depends(get_session_token)], service: AuthServiceDep
) -> User | None:
    """The signed-in user if there is a valid session, else None (never 401).

    For read-only endpoints anyone may call, where signing in shows more.
    """
    session = service.resolve_session(token) if token else None
    if session is None:
        return None
    bind_rls_user(service.db, session.user_id)
    return session.user


OptionalUser = Annotated[User | None, Depends(get_optional_user)]


def require_csrf(
    request: Request, session: Annotated[UserSession, Depends(get_current_session)]
) -> UserSession:
    """Session dependency that also enforces the synchronizer CSRF token."""
    if request.method not in SAFE_METHODS:
        provided = request.headers.get(CSRF_HEADER, "")
        if not provided or not tokens_match(session.csrf_token, provided):
            raise CsrfError("This request could not be verified. Refresh the page and try again.")
    return session


CurrentSession = Annotated[UserSession, Depends(require_csrf)]


def get_current_user(session: CurrentSession) -> User:
    return session.user


CurrentUser = Annotated[User, Depends(get_current_user)]


def get_council_access(council_id: uuid.UUID, user: CurrentUser, db: DbDep) -> CouncilAccess:
    return resolve_council_access(db, user, council_id)


CouncilAccessDep = Annotated[CouncilAccess, Depends(get_council_access)]
