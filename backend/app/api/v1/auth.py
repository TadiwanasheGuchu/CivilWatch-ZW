"""Authentication endpoints. Business rules live in app/services/auth.py."""

from typing import Annotated

from fastapi import APIRouter, Depends, Response, status

from app.api.deps import (
    AuthServiceDep,
    ClientContextDep,
    CurrentSession,
    SettingsDep,
    get_session_token,
)
from app.core.config import Settings
from app.models.identity import UserSession
from app.schemas.auth import LoginRequest, RegisterRequest, SessionResponse
from app.schemas.users import UserRead
from app.services.auth import IssuedSession

router = APIRouter(prefix="/auth", tags=["auth"])

_ERRORS = {
    401: {"description": "Not signed in or session expired"},
    403: {"description": "CSRF token missing or invalid, or cross-site request"},
    429: {"description": "Too many attempts; see Retry-After"},
}


def _session_response(session: UserSession) -> SessionResponse:
    return SessionResponse(
        user=UserRead.model_validate(session.user),
        csrf_token=session.csrf_token,
        expires_at=session.expires_at,
    )


def _set_session_cookie(response: Response, issued: IssuedSession, settings: Settings) -> None:
    response.set_cookie(
        key=settings.session_cookie_name,
        value=issued.token,
        max_age=settings.session_absolute_timeout_minutes * 60,
        path="/",
        secure=settings.session_cookie_secure,
        httponly=True,
        samesite="lax",
    )


def _clear_session_cookie(response: Response, settings: Settings) -> None:
    response.delete_cookie(
        key=settings.session_cookie_name,
        path="/",
        secure=settings.session_cookie_secure,
        httponly=True,
        samesite="lax",
    )


@router.post(
    "/register",
    status_code=status.HTTP_201_CREATED,
    response_model=SessionResponse,
    summary="Create a resident account and sign in",
    responses={409: {"description": "Email already registered"}, **_ERRORS},
)
def register(
    payload: RegisterRequest,
    response: Response,
    service: AuthServiceDep,
    client: ClientContextDep,
    settings: SettingsDep,
) -> SessionResponse:
    issued = service.register(
        email=payload.email,
        password=payload.password.get_secret_value(),
        full_name=payload.full_name,
        client=client,
    )
    _set_session_cookie(response, issued, settings)
    return _session_response(issued.session)


@router.post("/login", response_model=SessionResponse, summary="Sign in", responses=_ERRORS)
def login(
    payload: LoginRequest,
    response: Response,
    service: AuthServiceDep,
    client: ClientContextDep,
    settings: SettingsDep,
    previous_token: Annotated[str | None, Depends(get_session_token)],
) -> SessionResponse:
    issued = service.login(
        email=payload.email,
        password=payload.password.get_secret_value(),
        client=client,
        previous_token=previous_token,
    )
    _set_session_cookie(response, issued, settings)
    return _session_response(issued.session)


@router.post(
    "/logout",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Sign out of this session",
    responses=_ERRORS,
)
def logout(session: CurrentSession, service: AuthServiceDep, settings: SettingsDep) -> Response:
    service.logout(session)
    response = Response(status_code=status.HTTP_204_NO_CONTENT)
    _clear_session_cookie(response, settings)
    return response


@router.get(
    "/session",
    response_model=SessionResponse,
    summary="Current session, user and CSRF token",
    responses={401: _ERRORS[401]},
)
def current_session(session: CurrentSession) -> SessionResponse:
    return _session_response(session)
