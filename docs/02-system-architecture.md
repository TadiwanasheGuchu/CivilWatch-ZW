# 02 — System Architecture

## Shape

A **multi-tenant modular monolith**: one FastAPI backend, one Next.js frontend, one PostgreSQL + PostGIS database, Redis for caching/queues and Celery workers for background jobs. Microservices are explicitly out of scope until a measured need exists.

```
 Browser (mobile-first Next.js)
        │  HTTPS, JSON, cookie session
        ▼
 FastAPI  /api/v1  ───────────►  PostgreSQL 16 + PostGIS 3
   │  middleware: request ID, logging, security headers, CORS
   │  modules → services → repositories → SQLAlchemy models
   └──► Redis ◄── Celery worker (notifications, image processing)
                      └──► S3-compatible object storage (private) [Milestone 2]
```

## Backend layout (`backend/app/`)

| Package | Responsibility |
|---|---|
| `api/v1/` | Thin route handlers; dependency wiring only |
| `core/` | Settings, database engine/session, Redis, logging, errors, middleware |
| `models/` | SQLAlchemy ORM models (`Base`, UUID PK and timestamp mixins) |
| `schemas/` | Pydantic request/response schemas — never return ORM objects |
| `services/` | Business logic and transactions |
| `repositories/` | Query helpers where they improve organisation |
| `permissions/` | Role → permission mapping (`rbac.py`) and council access resolution (`council_access.py`) |
| `modules/` | Domain modules as they grow (identity, councils, issues, …) |
| `workers/` | Celery app and tasks |

Request flow: middleware assigns/propagates `X-Request-ID` → route → service → repository/ORM → schema → JSON. All errors leave via the single error envelope in `core/errors.py`.

## Frontend layout (`frontend/`)

| Folder | Responsibility |
|---|---|
| `app/` | App Router routes, root layout, providers |
| `components/` | Shared UI (`components/ui/` holds design-system primitives) |
| `features/<domain>/` | Domain features: API calls, hooks, components, types |
| `lib/` | API client, config, utilities |
| `tests/` | Vitest setup and Playwright E2E specs |

Server components by default; client components only where interactivity or TanStack Query is needed.

## Key decisions

| Decision | Status |
|---|---|
| Modular monolith, FastAPI + Next.js App Router | Adopted (CLAUDE.md) |
| psycopg 3 driver, synchronous SQLAlchemy sessions | Adopted — simpler transactions and testing; revisit only with measured need |
| Settings via environment, prefix `CIVICWATCH_` | Adopted |
| Structured JSON logs to stdout with `request_id` | Adopted |
| Server-side session authentication with synchronizer CSRF tokens | Approved and implemented (stage 1.2), see `06-security-and-privacy.md` |
| Tenant isolation via membership-derived scope + PostgreSQL RLS | Implemented (stage 1.3) |
| Two database roles: schema owner for migrations, unprivileged `civicwatch_app` for the API | Adopted (stage 1.3) — required for RLS to apply; see `06-security-and-privacy.md` |
| Layered packages (`api/`, `services/`, `repositories/`, `models/`, `schemas/`) with one file per domain, e.g. `services/auth.py` | Adopted; `modules/` reserved for a domain that outgrows this |
