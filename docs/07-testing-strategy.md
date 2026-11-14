# 07 — Testing Strategy

## Layers

| Layer | Tool | Location | Runs against |
|---|---|---|---|
| Backend unit/API | Pytest + HTTPX (`TestClient`) | `backend/tests/` | Real PostgreSQL + PostGIS and Redis — no database mocks |
| Frontend unit/component | Vitest + Testing Library | `frontend/**/*.test.ts(x)` | jsdom; `fetch` stubbed per test |
| End-to-end | Playwright | `frontend/tests/e2e/` | Running Next.js + real API |

Backend tests apply all Alembic migrations once per session, so every run also proves the migrations work. After each test the application tables are truncated and the Redis database flushed; the suite refuses to run unless `CIVICWATCH_ENVIRONMENT=test`. The test client uses an `https://` base URL so `Secure` cookies behave as in production. CI additionally runs `alembic check` to catch models without a migration.

Playwright runs every spec at 320, 375, 390, 768, 1024 and 1440 px widths and asserts no horizontal scrolling and ≥44px touch targets.

## Current coverage

- API conventions: error envelope (404/405), request-ID generation, propagation and sanitisation, security headers, CORS allow/deny, OpenAPI path, docs disabled in production.
- Health: liveness, readiness OK, readiness degraded (503) when Redis is down.
- Authentication: registration (normalisation, Argon2id storage, hashed session tokens, hardened cookie attributes, duplicate emails, validation incl. privilege-field injection), sign-in (identical failures for wrong password/unknown email, inactive users, account lockout and reset, per-IP registration limit), sessions (absolute and idle expiry, activity extension, forged cookies, server-side revocation on logout and re-login, replay of a revoked cookie), CSRF (missing token, token from another session), cross-origin login rejected, credentials absent from logs.
- Account: own profile only, CSRF on updates, no privilege escalation, password change signs out other sessions, wrong current password and its rate limit, stale-session purge.
- Settings: production refuses insecure cookies; `__Host-` cookies require `Secure`.
- Councils: public directory and pagination, creation limited to platform admins (with CSRF and slug rules), workspace permissions per role, residents and unknown councils refused, platform admin without operational access.
- Staff management: add/change/remove with immediate loss of access, re-appointment keeps history, unknown email/duplicate/invalid role, officers cannot add staff or promote themselves, last administrator protected, every change audited with actor and request ID.
- **Tenant isolation (mandatory)**: council A's administrator cannot read B's workspace, staff or audit log, cannot add, change or remove B's staff, cannot reach B's membership through A's URL, sees only A's rows in lists; council IDs in bodies are rejected; a person in two councils has the right role in each.
- **Row-Level Security at the database**, as the API's role: the role cannot bypass RLS; unfiltered queries return only the user's councils; no identity → no rows; residents see nothing; cross-council inserts are refused and updates affect no rows; the audit log cannot be updated or deleted; audit entries cannot impersonate another actor; the identity does not leak between transactions on pooled connections.
- Operator CLI: granting and revoking platform admin, audited.
- Frontend: API error mapping; status panel OK, degraded and unreachable states.
- E2E: home page layout at six widths; live status from the real API; touch target size.

## Mandatory security tests (added with the features they protect)

Cross-council private-report access · residents modifying others' reports · unauthorised assignment · public access to private media · private data in public analytics · invalid status transitions.

## Running locally

```bash
cd backend && pytest
```

```bash
cd frontend && npm test && npm run test:e2e
```

Backend tests need a disposable database (e.g. `civicwatch_test`) with the `civicwatch_app` login role, and Redis:

- `CIVICWATCH_DATABASE_URL` — as `civicwatch_app` (so RLS is exercised exactly as in production);
- `CIVICWATCH_MIGRATION_DATABASE_URL` — as the schema owner (migrations and per-test cleanup);
- `CIVICWATCH_REDIS_URL`.
