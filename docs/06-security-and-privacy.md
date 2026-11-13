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
- **Audit logging** of sign-ins and password changes is planned with the `audit_logs` table in stage 1.3; today these events go to structured logs with the user ID only.

Why sessions rather than JWTs: immediate revocation, no token in JavaScript-accessible storage, and a smaller XSS blast radius.

## Tenant isolation (approved; implementation in stage 1.3)

- The council scope of every request is derived from the authenticated user's `council_memberships`, never from a client-supplied council ID.
- Service-layer checks (`permissions/`) reject access before queries run; repositories always filter by the permitted council IDs.
- Defence in depth with PostgreSQL **Row-Level Security** on council-owned tables, using a per-transaction `SET LOCAL app.user_id` and an application role that is not the table owner.
- Every platform-admin action is written to `audit_logs`.

## Privacy rules (from CLAUDE.md §8)

Private reports, their photos, coordinates, reporter contact details, internal notes and unauthorised comments are never returned to unauthorised users or included in public analytics. Uploaded media is stored privately and served only through short-lived signed URLs; EXIF metadata is stripped.
