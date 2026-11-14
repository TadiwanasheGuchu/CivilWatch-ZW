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
                      └──► S3-compatible object storage (private; MinIO locally)
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
| `features/<domain>/` | Domain features: API calls, hooks, components, types. Current: `authentication`, `council`, `reporting` (report form in `reporting/wizard/`), `maps`, `navigation`, `system-status` |
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
| Report locations stored as `geography(Point, 4326)` with a GiST index | Adopted (stage 2.1) — metre-accurate distance queries for nearby search and clustering later |
| Photos uploaded through the API (not directly to storage), re-encoded with Pillow, stored in a private S3-compatible bucket (`boto3`), served only by pre-signed URLs | Adopted (stage 2.2) — the server must see and sanitise every file before it is stored |
| Local and CI storage: MinIO (pinned community image); tests fall back to the `moto` S3 emulator when no real service is configured | Adopted (stage 2.2) |
| Report drafts kept in the browser's IndexedDB (photos as Blobs), with an in-memory fallback | Adopted (stage 2.3) — offline drafting on budget phones |
| Photos compressed in the browser before upload (≤1600 px JPEG); uploads use XMLHttpRequest for progress | Adopted (stage 2.3) — saves mobile data; the server still validates and re-encodes |
| MapLibre GL JS with raster tiles, loaded only when a map is shown; its worker served from `public/maplibre/` | Adopted (stage 2.3) |
| Status workflow as one declarative table (`services/workflow.py`): permission, scope (council, department, assignee) and note rule per transition; the API offers each caller exactly the transitions they may make | Adopted (stage 3.1) |
| Status changes lock the report row (`SELECT … FOR UPDATE`) so concurrent changes cannot both succeed | Adopted (stage 3.1) |
| Layered packages (`api/`, `services/`, `repositories/`, `models/`, `schemas/`) with one file per domain, e.g. `services/auth.py` | Adopted; `modules/` reserved for a domain that outgrows this |
