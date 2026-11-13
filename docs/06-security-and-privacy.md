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

## Proposed: authentication (awaiting approval)

- Email + password, hashed with **Argon2id** (`argon2-cffi`).
- **Server-side sessions**: a random 256-bit token in an `HttpOnly; Secure; SameSite=Lax` cookie; only its SHA-256 hash is stored (`user_sessions`), with idle and absolute expiry and server-side revocation on logout/password change.
- **CSRF**: double-submit token sent in the `X-CSRF-Token` header on every state-changing request (the API already allows this header in CORS).
- Login and registration rate-limited per IP and per account (Redis).

Why sessions rather than JWTs: immediate revocation, no token in JavaScript-accessible storage, and a smaller XSS blast radius.

## Proposed: tenant isolation (awaiting approval)

- The council scope of every request is derived from the authenticated user's `council_memberships`, never from a client-supplied council ID.
- Service-layer checks (`permissions/`) reject access before queries run; repositories always filter by the permitted council IDs.
- Defence in depth with PostgreSQL **Row-Level Security** on council-owned tables, using a per-transaction `SET LOCAL app.user_id` and an application role that is not the table owner.
- Every platform-admin action is written to `audit_logs`.

## Privacy rules (from CLAUDE.md §8)

Private reports, their photos, coordinates, reporter contact details, internal notes and unauthorised comments are never returned to unauthorised users or included in public analytics. Uploaded media is stored privately and served only through short-lived signed URLs; EXIF metadata is stripped.
