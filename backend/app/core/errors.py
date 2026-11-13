"""Consistent API error responses.

Every error leaves the API in the same envelope:

    {"error": {"code": "...", "message": "...", "details": ..., "request_id": "..."}}
"""

import logging
from http import HTTPStatus
from typing import Any

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.core.logging import request_id_var

logger = logging.getLogger(__name__)


class AppError(Exception):
    """Base class for expected, client-facing errors raised by services."""

    status_code: int = 400
    code: str = "bad_request"

    def __init__(
        self, message: str, *, details: Any = None, headers: dict[str, str] | None = None
    ) -> None:
        super().__init__(message)
        self.message = message
        self.details = details
        self.headers = headers


class NotFoundError(AppError):
    status_code = 404
    code = "not_found"


class PermissionDeniedError(AppError):
    status_code = 403
    code = "permission_denied"


class AuthenticationError(AppError):
    status_code = 401
    code = "authentication_required"


class ConflictError(AppError):
    status_code = 409
    code = "conflict"


class RateLimitedError(AppError):
    status_code = 429
    code = "rate_limited"

    def __init__(self, message: str, *, retry_after_seconds: int) -> None:
        super().__init__(
            message,
            details={"retry_after_seconds": retry_after_seconds},
            headers={"Retry-After": str(retry_after_seconds)},
        )


class ServiceUnavailableError(AppError):
    status_code = 503
    code = "service_unavailable"


def error_body(code: str, message: str, details: Any = None) -> dict[str, Any]:
    return {
        "error": {
            "code": code,
            "message": message,
            "details": details,
            "request_id": request_id_var.get(),
        }
    }


def _status_code_slug(status_code: int) -> str:
    try:
        return HTTPStatus(status_code).phrase.lower().replace(" ", "_").replace("-", "_")
    except ValueError:
        return "error"


async def _app_error_handler(_: Request, exc: Exception) -> JSONResponse:
    assert isinstance(exc, AppError)
    return JSONResponse(
        status_code=exc.status_code,
        content=error_body(exc.code, exc.message, exc.details),
        headers=exc.headers,
    )


async def _http_error_handler(_: Request, exc: Exception) -> JSONResponse:
    assert isinstance(exc, StarletteHTTPException)
    message = exc.detail if isinstance(exc.detail, str) else HTTPStatus(exc.status_code).phrase
    return JSONResponse(
        status_code=exc.status_code,
        content=error_body(_status_code_slug(exc.status_code), message),
        headers=getattr(exc, "headers", None),
    )


async def _validation_error_handler(_: Request, exc: Exception) -> JSONResponse:
    assert isinstance(exc, RequestValidationError)
    details = [
        {"location": list(err.get("loc", ())), "message": err.get("msg"), "type": err.get("type")}
        for err in exc.errors()
    ]
    return JSONResponse(
        status_code=422,
        content=error_body("validation_error", "The request contains invalid data.", details),
    )


async def _unhandled_error_handler(_: Request, exc: Exception) -> JSONResponse:
    # Log the full exception server-side; never leak internals to the client.
    logger.exception("Unhandled server error", exc_info=exc)
    return JSONResponse(
        status_code=500,
        content=error_body("internal_error", "An unexpected error occurred."),
    )


def register_error_handlers(app: FastAPI) -> None:
    app.add_exception_handler(AppError, _app_error_handler)
    app.add_exception_handler(StarletteHTTPException, _http_error_handler)
    app.add_exception_handler(RequestValidationError, _validation_error_handler)
    app.add_exception_handler(Exception, _unhandled_error_handler)
