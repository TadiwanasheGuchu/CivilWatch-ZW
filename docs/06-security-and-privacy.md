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
  - Idle timeout 7 days, absolute lifetime 30 days (configurable). These suit residents on shared or intermittently connected phones; shorter limits for council staff are planned with roles in stage 1.3.
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

- Staff sessions use the same timeouts as residents (7 days idle / 30 days absolute). Shorter staff limits are planned for stage 1.4, together with the staff sign-in UI.
- There is no API yet to deactivate a council or a user account; this is done by an operator and will get an audited workflow.

## Privacy rules (from CLAUDE.md §8)

Private reports, their photos, coordinates, reporter contact details, internal notes and unauthorised comments are never returned to unauthorised users or included in public analytics. Uploaded media is stored privately and served only through short-lived signed URLs; EXIF metadata is stripped.
