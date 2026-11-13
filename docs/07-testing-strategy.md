# 07 — Testing Strategy

## Layers

| Layer | Tool | Location | Runs against |
|---|---|---|---|
| Backend unit/API | Pytest + HTTPX (`TestClient`) | `backend/tests/` | Real PostgreSQL + PostGIS and Redis — no database mocks |
| Frontend unit/component | Vitest + Testing Library | `frontend/**/*.test.ts(x)` | jsdom; `fetch` stubbed per test |
| End-to-end | Playwright | `frontend/tests/e2e/` | Running Next.js + real API |

Backend tests apply all Alembic migrations once per session, so every run also proves the migrations work. CI additionally runs `alembic check` to catch models without a migration.

Playwright runs every spec at 320, 375, 390, 768, 1024 and 1440 px widths and asserts no horizontal scrolling and ≥44px touch targets.

## Current coverage

- API conventions: error envelope (404/405), request-ID generation, propagation and sanitisation, security headers, CORS allow/deny, OpenAPI path, docs disabled in production.
- Health: liveness, readiness OK, readiness degraded (503) when Redis is down.
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
