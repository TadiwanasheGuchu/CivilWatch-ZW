# 04 — API Specification

Base path: `/api/v1`. Interactive OpenAPI docs: `/docs` (disabled in production); schema: `/api/v1/openapi.json`.

## Conventions

- JSON request and response bodies with explicit Pydantic schemas.
- Every response carries `X-Request-ID`. A caller may send its own (8–64 chars of `A-Za-z0-9._-`); anything else is replaced.
- Collections are paginated (cursor or `page`/`page_size`, max 100) — defined with the first collection endpoint.
- Status changes use dedicated action endpoints (e.g. `POST /issues/{id}/transitions`), never a generic PATCH.

### Error envelope

Every error, including 404/405/422/500, uses:

```json
{
  "error": {
    "code": "validation_error",
    "message": "The request contains invalid data.",
    "details": [{ "location": ["body", "email"], "message": "...", "type": "..." }],
    "request_id": "4f0c…"
  }
}
```

`code` is a stable machine-readable slug; `message` is safe to show users; 500 responses never include internal details.

## Implemented endpoints

### `GET /api/v1/health/live`
Process liveness. Unauthenticated. `200 {"status": "ok"}`.

### `GET /api/v1/health/ready`
Dependency readiness. Unauthenticated; reveals only coarse status.

```json
{ "status": "ok", "database": "ok", "postgis": "ok", "cache": "ok" }
```

Returns `503` with the same shape and `"status": "degraded"` when any dependency is unavailable.

## Authentication model

- Signing in sets an `HttpOnly; Secure; SameSite=Lax` session cookie (`__Host-cw_session` in production). Browsers must send requests with credentials (`fetch(..., { credentials: "include" })`).
- Sign-in responses and `GET /auth/session` return a `csrf_token`. Every `POST`/`PUT`/`PATCH`/`DELETE` made with a session must send it as `X-CSRF-Token`, otherwise `403 csrf_token_invalid`.
- State-changing requests carrying an `Origin` header that is not an allowed frontend origin are refused with `403 origin_not_allowed`.
- `401 authentication_required` means there is no valid session (missing, expired, idle, revoked, or the account was deactivated).
- `429 rate_limited` includes a `Retry-After` header and `details.retry_after_seconds`.

`SessionResponse`:

```json
{
  "user": {
    "id": "uuid", "email": "tendai@example.com", "full_name": "Tendai Moyo",
    "is_platform_admin": false, "created_at": "2026-11-13T19:14:17Z"
  },
  "csrf_token": "…",
  "expires_at": "2026-12-13T19:14:17Z"
}
```

### `POST /api/v1/auth/register`
Body `{ "email", "password", "full_name" }`. Password 10–128 characters, not only spaces, not equal to the email. Unknown fields are rejected. `201 SessionResponse` and session cookie. `409 conflict` if the email is registered. Rate limit: 10 per IP per hour.

### `POST /api/v1/auth/login`
Body `{ "email", "password" }`. `200 SessionResponse` and a new session cookie; a session cookie already held by this browser is revoked. Wrong password, unknown email and deactivated account all return the same `401` message. Rate limits: 30 attempts per IP and 5 failures per account per 15 minutes; once an account is locked even the correct password receives `429` until the window ends.

### `POST /api/v1/auth/logout`
Requires session + CSRF. `204`; the session is revoked server-side and the cookie cleared.

### `GET /api/v1/auth/session`
`200 SessionResponse` for the current session, or `401`. The frontend calls this on load to learn who is signed in and obtain the CSRF token.

### `GET /api/v1/users/me`
`200` with the signed-in user's profile (same shape as `SessionResponse.user`).

### `PATCH /api/v1/users/me`
Requires CSRF. Body `{ "full_name" }` only — any other field (e.g. `is_platform_admin`) is a `422`. `200` with the updated profile.

### `POST /api/v1/users/me/password`
Requires CSRF. Body `{ "current_password", "new_password" }`. `204` on success; every other session of the account is revoked. `400 invalid_current_password` if the current password is wrong (5 attempts per 15 minutes, then `429`). `422` if the new password is invalid or unchanged.

## Planned endpoint groups

`/auth`, `/users`, `/councils`, `/departments`, `/issues`, `/assignments`, `/map`, `/analytics`, `/notifications` — each documented here when implemented.
