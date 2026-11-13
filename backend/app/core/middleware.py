"""HTTP middleware: request correlation IDs, request logging, security headers."""

import logging
import re
import time
import uuid

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import JSONResponse, Response
from starlette.types import ASGIApp

from app.core.errors import error_body
from app.core.logging import request_id_var

logger = logging.getLogger("civicwatch.request")

REQUEST_ID_HEADER = "X-Request-ID"
# Accept a caller-supplied ID only if it is short and safe to log.
_VALID_REQUEST_ID = re.compile(r"^[A-Za-z0-9._-]{8,64}$")


class RequestContextMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        incoming = request.headers.get(REQUEST_ID_HEADER, "")
        request_id = incoming if _VALID_REQUEST_ID.match(incoming) else uuid.uuid4().hex
        token = request_id_var.set(request_id)
        started = time.perf_counter()
        try:
            response = await call_next(request)
        finally:
            request_id_var.reset(token)
        duration_ms = round((time.perf_counter() - started) * 1000, 2)
        response.headers[REQUEST_ID_HEADER] = request_id
        # Path only — query strings may carry personal data.
        logger.info(
            "request completed",
            extra={
                "request_id": request_id,
                "method": request.method,
                "path": request.url.path,
                "status_code": response.status_code,
                "duration_ms": duration_ms,
            },
        )
        return response


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Baseline hardening headers for a JSON API."""

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        response = await call_next(request)
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("X-Frame-Options", "DENY")
        response.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
        response.headers.setdefault("Cross-Origin-Resource-Policy", "same-site")
        if not request.url.path.startswith(("/docs", "/redoc")):
            response.headers.setdefault(
                "Content-Security-Policy", "default-src 'none'; frame-ancestors 'none'"
            )
        return response


class OriginCheckMiddleware(BaseHTTPMiddleware):
    """Reject state-changing browser requests from origins we do not serve.

    Browsers always send `Origin` on cross-origin POST/PUT/PATCH/DELETE, so a
    forged form or fetch from another site is refused before it reaches a
    handler. This also covers endpoints with no session yet (login CSRF).
    Non-browser clients that send no Origin are unaffected; authenticated
    requests are additionally protected by the session CSRF token.
    """

    UNSAFE_METHODS = frozenset({"POST", "PUT", "PATCH", "DELETE"})

    def __init__(self, app: ASGIApp, allowed_origins: list[str]) -> None:
        super().__init__(app)
        self.allowed_origins = frozenset(origin.rstrip("/") for origin in allowed_origins)

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        origin = request.headers.get("Origin")
        if (
            request.method in self.UNSAFE_METHODS
            and origin is not None
            and origin.rstrip("/") not in self.allowed_origins
        ):
            logger.warning("cross-origin request rejected", extra={"path": request.url.path})
            return JSONResponse(
                status_code=403,
                content=error_body(
                    "origin_not_allowed", "Requests from this website are not allowed."
                ),
            )
        return await call_next(request)
