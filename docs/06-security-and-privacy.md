# 06 — Security and Privacy

## Implemented controls (foundation)

- Secrets only from environment variables; `.env` is git-ignored; `.env.example` holds non-secret local defaults. Docker Compose refuses to start without `POSTGRES_PASSWORD`.
- Security headers on API responses: `X-Content-Type-Options`, `X-Frame-Options: DENY`, `Referrer-Policy`, `Cross-Origin-Resource-Policy`, restrictive `Content-Security-Policy`. Frontend sets equivalent headers plus a `Permissions-Policy` that allows only camera and geolocation for this origin.
- CORS restricted to configured origins (`CIVICWATCH_CORS_ORIGINS`), tested.
- Uniform error envelope; unhandled exceptions are logged server-side and never leak internals.
- Request logs record method, path, status and duration — **not** query strings, bodies or headers, so tokens and personal data are not logged.
- Incoming `X-Request-ID` is validated to prevent log/header injection.
- OpenAPI docs disabled in production.
- Containers run as non-root users; local service ports bind to `127.0.0.1` only.

## Authentication (implemented, stage 1.2)

- Email + password, hashed with **Argon2id** (`argon2-cffi`; t=3, m=64 MiB, p=4, pinned in `core/security.py`). Hashes are upgraded on the next sign-in if parameters change.
- Failed sign-ins for unknown emails still run a full Argon2 verification against a dummy hash, so response time does not reveal which emails are registered. Wrong password, unknown email and deactivated account return the same message.
- **Server-side sessions**: a random 256-bit token in an `HttpOnly; Secure; SameSite=Lax` cookie named `__Host-cw_session` (host-only, Path=/). Only its SHA-256 hash is stored in `user_sessions`.
  - Residents: idle timeout 7 days, absolute lifetime 30 days, suited to shared or intermittently connected phones.
  - Council staff and platform admins: idle timeout **12 hours** (a working shift) and absolute lifetime **7 days**, because their sessions reach other people's data. The stricter limits are checked only for sessions already past them, so normal requests pay nothing extra; a session found over the limit is revoked. Someone removed from all councils returns to resident limits. All four values are configurable; staff limits may not exceed resident limits.
  - Revoked on logout, when the same browser signs in again, and (for all *other* sessions) on password change. Deactivating a user invalidates their sessions immediately.
  - Staging/production refuse to start unless the cookie is `Secure`.
- **CSRF**: synchronizer token. Each session has its own random `csrf_token`, returned in the sign-in response and `GET /auth/session` (never in a cookie, so it works when the API and web app are on different hosts). Every state-changing request with a session must echo it in `X-CSRF-Token`; comparison is constant-time.
- **Cross-origin check**: state-changing requests whose `Origin` is not an allowed frontend origin are rejected before reaching any handler. This also blocks *login CSRF* (signing a victim into an attacker's account), which session tokens alone cannot prevent.
- **Rate limiting** (Redis fixed windows; identifiers are hashed before use as keys): registration 10/IP/hour; sign-in 30 attempts/IP and 5 failures/account per 15 minutes, with locked accounts refused before the password is checked; password change 5/user per 15 minutes. Limits **fail closed**: if Redis is down, auth endpoints return 503 rather than run unprotected.
- Request schemas reject unknown fields (`extra="forbid"`), so fields such as `is_platform_admin` cannot be set through the API. Validation errors never echo submitted values.
- Passwords are `SecretStr` in schemas and are never logged; tests assert that neither passwords, session tokens nor emails appear in logs.

### Known limitations / accepted risks

- **Email enumeration via registration**: `POST /auth/register` returns `409` for a registered email. Hiding this requires email verification, which needs an email provider (not yet chosen). Mitigated by the per-IP registration limit. Revisit when email delivery lands.
- **No email verification or password reset yet** — both need an email/SMS provider decision (see open questions in `01-product-requirements.md`).
- **No breached-password check** yet; candidate: a bundled top-passwords list or the k-anonymity Pwned Passwords API.
- **Client IP behind a proxy**: production must run uvicorn with `--proxy-headers` and a strict `--forwarded-allow-ips`, otherwise all clients share the proxy's IP for rate limiting.
- **Audit logging**: password changes and platform-admin grants are audited; individual sign-ins and failures go to structured logs only, to keep the audit trail focused on changes.

Why sessions rather than JWTs: immediate revocation, no token in JavaScript-accessible storage, and a smaller XSS blast radius.

## Tenant isolation (implemented, stage 1.3)

Three independent layers; each would stop a cross-council read on its own.

1. **Access resolution** (`permissions/council_access.py`): for `/councils/{id}/…`, the caller's active membership in *that* council is loaded from the database and mapped to permissions (`permissions/rbac.py`). The council ID in the URL only selects; it grants nothing. Request bodies reject unknown fields, so a council ID cannot be smuggled in.
2. **Explicit query filters**: every repository query on council-owned data filters by the resolved council ID — e.g. a membership ID from another council is simply not found.
3. **PostgreSQL Row-Level Security**: the API connects as `civicwatch_app`, which owns no tables, has no `BYPASSRLS`, and holds only the privileges it needs. Each authenticated transaction carries the user ID in a transaction-local setting, and policies restrict `council_memberships` and `audit_logs` to the user's own councils (see `03-database-design.md`). A query that forgot its filter still returns only permitted rows. Tests assert the API role cannot bypass RLS.

**Platform administrators** can create councils and manage staff (to appoint first administrators) but have no operational access without a membership. They are appointed only with `python -m app.cli grant-platform-admin <email>` on the server, never through the API. Every administrative action, and every staff change, writes an `audit_logs` entry in the same transaction, with `via_platform_admin` recorded.

**Audit trail integrity**: `civicwatch_app` has only SELECT and INSERT on `audit_logs`, so entries cannot be altered or deleted through the application; RLS also prevents writing an entry in someone else's name.

**Last administrator**: a council cannot lose its final `council_admin`; the check locks the administrators' rows so concurrent changes cannot both pass.

### Remaining limitations

- There is no API yet to deactivate a council or a user account; this is done by an operator and will get an audited workflow.

## Report privacy (stage 2.1)

- **Who sees a report** is decided twice: explicitly in `IssueService.get_for_viewer` and the repository's publication filter, and again by RLS on `issues` (see `03-database-design.md`). Tests prove each layer on its own.
- **Unpublished means invisible.** A PUBLIC report is hidden from everyone except its reporter and council staff until the council verifies it. This blocks abusive content and personal data in a report before a person has looked at it.
- **Public responses never identify the reporter**: no reporter ID, name or email, and no visibility flag.
- **No modification after submission** through the API, and the API role has no `UPDATE`/`DELETE` privilege on `issues` or `issue_status_history`. Status changes will only happen through Milestone 3's validated transitions, each recorded in the history.
- **Location checks**: coordinates must be valid, inside the service area, and inside the chosen council's boundary when known (PostGIS `ST_Covers`). Choosing a council is only addressing the report; it grants no council access.
- **Abuse limits**: an account is required, and each user may submit 20 reports per hour (configurable, fails closed if Redis is down).

## Photo uploads (stage 2.2)

- **Content, not claims, decides.** Uploads are decoded with Pillow; only real JPEG, PNG and WebP pass, whatever the file name or `Content-Type` says. HTML, PDF, GIF, BMP, truncated and empty files are refused.
- **Nothing is stored as received.** Every photo is re-encoded from its pixels into a new JPEG. This removes all EXIF (including **GPS location**, camera make and software), XMP and ICC data, and drops anything hidden in or appended to the file. The camera's rotation is applied first, so photos still display the right way up. There is no separate virus scan: the original bytes are never stored or served.
- **Resource limits**: 10 MB per upload (checked from `Content-Length` before reading, and again while reading); 40 megapixels per image, so tiny "decompression bomb" files are refused; 5 photos per report; 60 uploads per user per hour.
- **Private storage**: the bucket is private. The API stores object keys, never URLs, and returns pre-signed GET URLs valid for 5 minutes, only for reports the caller may see. Unpublished and private report photos are never signed for anyone but the reporter (and, from Milestone 3, that council's staff). Locally the API uses its own storage account limited to the media bucket.
- **Who may upload**: only the reporter, only while the report is `SUBMITTED` (API check and RLS insert policy). Concurrent uploads cannot exceed the per-report limit (transaction-scoped advisory lock).
- **Failure handling**: if storage is down, the upload fails with 503 and nothing is recorded; if the database write fails after storing, the stored objects are deleted.
- **Not yet done**: residents cannot delete a photo they added by mistake (planned with the report form in 2.3); HEIC photos are not accepted (browsers on Android and iOS normally upload JPEG).

## Council operations (stage 3.1)

- **Least privilege per role**, decided by one transition table and enforced in the API; each response tells the caller exactly which changes they may make, so the UI never guesses. Department managers act only within their department, maintenance officers only on work assigned to them, and platform admins have no access to reports.
- **Messages vs. internal notes**: a status change may carry a message to the reporter. Staff-only notes live in a separate table that only council staff can read (API and RLS) and that cannot be edited or deleted. Public timelines show statuses only.
- **Reporter privacy**: staff see the reporter's name, never their email or any other contact detail.
- **Database backstops**: the API role may update only a report's status (and duplicate link), only as staff of that council, or as the reporter answering a request for information (and then only back to review). Departments are created only by the council's administrators; assignments and notes are invisible outside the council. Composite foreign keys make it impossible to attach another council's department to a membership or assignment.

## Frontend

- The browser never sees the session token (HttpOnly cookie). The CSRF token is held only in memory (the TanStack Query cache) and re-fetched from `GET /auth/session` on page load.
- Route guards (`RequireSession`) and permission-based tabs only shape the UI; every API call is authorised again by the backend.
- `?next=` redirects after sign-in accept only same-site paths (`safeNextPath`), so crafted links cannot send people to another website.
- Signing out reloads the home page, discarding every cached response; when a different user signs in on the same tab, cached data from the previous user is dropped.
- Any 401 or CSRF rejection refreshes the session, so expired or revoked sessions are reflected immediately.
- User-provided text is rendered as text by React, never as HTML.
- **Drafts on the device**: unsent reports, including photos, are stored in the browser's IndexedDB and never leave the phone until sent. Signing out deletes them. Photos are re-encoded in the browser before upload, which also drops their EXIF data on most phones; the server strips metadata regardless.
- Photo images are shown from short-lived signed URLs and are never passed through Next.js image optimisation, which could cache them.

## Privacy rules (from CLAUDE.md §8)

Private reports, their photos, coordinates, reporter contact details, internal notes and unauthorised comments are never returned to unauthorised users or included in public analytics. Uploaded media is stored privately and served only through short-lived signed URLs; EXIF metadata is stripped.
