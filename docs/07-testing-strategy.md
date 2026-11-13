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

Backend tests need `CIVICWATCH_DATABASE_URL` pointing at a disposable database (e.g. `civicwatch_test`) and Redis on `CIVICWATCH_REDIS_URL`.
