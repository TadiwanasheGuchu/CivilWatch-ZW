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
{ "status": "ok", "database": "ok", "postgis": "ok", "cache": "ok", "storage": "ok" }
```

Returns `503` with the same shape and `"status": "degraded"` when any dependency is unavailable.

## Authentication model

- Signing in sets an `HttpOnly; Secure; SameSite=Lax` session cookie (`__Host-cw_session` in production). Browsers must send requests with credentials (`fetch(..., { credentials: "include" })`).
- Sign-in responses and `GET /auth/session` return a `csrf_token`. Every `POST`/`PUT`/`PATCH`/`DELETE` made with a session must send it as `X-CSRF-Token`, otherwise `403 csrf_token_invalid`.
- State-changing requests carrying an `Origin` header that is not an allowed frontend origin are refused with `403 origin_not_allowed`.
- `401 authentication_required` means there is no valid session (missing, expired, idle, revoked, or the account was deactivated). Council staff and platform admins have shorter session limits than residents (see `06-security-and-privacy.md`).
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

### `GET /api/v1/users/me/memberships`
The councils where the signed-in user is active staff — the workspace switcher. Each item: `{ id, council: { id, slug, name }, role, created_at }`. Residents get `[]`.

## Councils

Pagination for collections: `?page=1&page_size=20` (max 100). Response `{ "items": [...], "page", "page_size", "total" }`.

Access to `/councils/{council_id}/…` is decided from the caller's own active membership (or platform-admin flag). A council ID in the URL selects the council but never grants access; request bodies cannot carry a council ID (unknown fields are rejected). Not a member → `403`; unknown or inactive council → `404`; a membership ID that belongs to a different council → `404`.

| Permission | council_admin | department_manager | verification_officer | maintenance_officer | platform admin (no membership) |
|---|---|---|---|---|---|
| `workspace.view` | ✓ | ✓ | ✓ | ✓ | — |
| `members.view` | ✓ | ✓ | ✓ | ✓ | ✓ |
| `members.manage` | ✓ | — | — | — | ✓ |
| `audit.view` | ✓ | — | — | — | ✓ |

### `GET /api/v1/councils`
Public directory of active councils, sorted by name: `Page<{ id, slug, name }>`. No sign-in required.

### `POST /api/v1/councils`
Platform admins only (CSRF). Body `{ "slug", "name" }`; slug 3–60 chars, lowercase letters/digits with single hyphens. `201 { id, slug, name }`; `409` if the slug exists. Audited as `council.created`.

### `GET /api/v1/councils/{council_id}/workspace`
`{ council, role, via_platform_admin, permissions[] }` for the caller. Informational for the UI; the backend re-checks permissions on every request.

### `GET /api/v1/councils/{council_id}/members`
`members.view`. `Page<{ membership_id, user_id, full_name, email, role, granted_at }>`, active staff only.

### `POST /api/v1/councils/{council_id}/members`
`members.manage` (CSRF). Body `{ "email", "role" }`. `201` member. `404` if no active account uses the email; `409` if already an active member; `422` for an unknown role (including `resident`). Audited as `membership.granted`.

### `PATCH /api/v1/councils/{council_id}/members/{membership_id}`
`members.manage` (CSRF). Body `{ "role" }`. `200` member. `409 last_council_admin` if it would leave the council without an administrator. Audited as `membership.role_changed`.

### `DELETE /api/v1/councils/{council_id}/members/{membership_id}`
`members.manage` (CSRF). `204`; sets `revoked_at` (history kept) and access ends immediately. `409 last_council_admin` as above. Audited as `membership.revoked`.

### `GET /api/v1/councils/{council_id}/audit-logs`
`audit.view`. Newest first: `Page<{ id, occurred_at, actor_user_id, actor_name, action, target_type, target_id, details, request_id }>`. `actor_name` is the actor's current name, or `null` for system and command-line actions.

## Reports

A report is visible to its reporter at any time, and to everyone once it is `PUBLIC` and verified by the council (`VERIFIED`, `ASSIGNED`, `IN_PROGRESS`, `RESOLVED` or `CLOSED`). Anything else is `404` to other callers, so its existence is not revealed. Council staff views and status changes arrive in Milestone 3. Reports have no update or delete endpoints: `PUT`, `PATCH` and `DELETE` on `/issues/{id}` return `405`.

### `GET /api/v1/categories`
Public. The active categories in display order: `[{ id, code, name, description }]`.

### `POST /api/v1/issues`
Signed in, with CSRF. Body:

```json
{
  "council_id": "uuid", "category_id": "uuid",
  "title": "Large pothole on Samora Machel Avenue",
  "description": "Deep pothole in the left lane…",
  "latitude": -17.8292, "longitude": 31.0522,
  "location_description": "Outside the main post office",
  "visibility": "PUBLIC"
}
```

Title 5–120 characters (single line), description 10–2000, `location_description` optional (≤200), no control characters. Unknown fields (e.g. `status`, `reporter_id`) are rejected. `201 OwnIssue`. Business-rule failures use the standard `422 validation_error` envelope with the offending field in `details[].location`: unknown or inactive council (`council_id`), unknown category (`category_id`), location outside the service area or outside the council's known boundary (`latitude`). `429` after 20 reports per user per hour.

`OwnIssue`: `{ id, reference, council: { id, slug, name }, category: { code, name }, title, description, status, latitude, longitude, location_description, created_at, updated_at, photo_count, cover_thumbnail_url, visibility, is_published }`. `cover_thumbnail_url` is a signed URL for the first photo's thumbnail, or `null`.

### `GET /api/v1/issues/mine`
Signed in. The caller's own reports, newest first, any visibility: `Page<OwnIssue>`.

### `GET /api/v1/issues`
Public. Published public reports, newest first: `Page<PublicIssue>`. Filters: `council_id`, `category` (a category code), `status` (one of the published statuses; anything else is `422`). `PublicIssue` is `OwnIssue` without `visibility` and `is_published`, and never identifies the reporter.

### `GET /api/v1/issues/{issue_id}`
Public; signing in lets reporters see their own unpublished or private reports. Returns the report plus `history: [{ from_status, to_status, created_at }]` and `photos: [{ id, url, thumbnail_url, width, height }]`, as `OwnIssueDetail` for the reporter or `PublicIssueDetail` for everyone else. `404` if the caller may not see it.

### `DELETE /api/v1/issues/{issue_id}/photos/{photo_id}`
Signed in, with CSRF. The reporter may remove a photo while the report is `SUBMITTED`. `204`; the stored photo and thumbnail are deleted. `404` if it is not your report or the photo does not exist; `409 report_locked` once the council has started.

**Photo URLs** are pre-signed and expire after `CIVICWATCH_MEDIA_URL_TTL_SECONDS` (default 5 minutes). Fetch the report again for fresh URLs. They are generated only for reports the caller may see.

### `POST /api/v1/issues/{issue_id}/photos`
Signed in, with CSRF; `multipart/form-data` with one `file` field. Only the reporter, and only while the report is `SUBMITTED`. JPEG, PNG or WebP up to 10 MB; the stored photo is a re-encoded JPEG of at most 1600 px (plus a 400 px thumbnail) with all metadata removed. `201 { id, url, thumbnail_url, width, height }`. Errors: `404` not your report; `409 report_locked` once the council has started on it; `409 photo_limit_reached` after 5 photos; `413 photo_too_large`; `422 invalid_photo` for anything that is not a readable JPEG/PNG/WebP or is over 40 megapixels; `429` after 60 uploads per hour; `503` if storage is unavailable (nothing is saved).

## Planned endpoint groups

`/departments`, `/assignments`, `/map`, `/analytics`, `/notifications` — each documented here when implemented.
