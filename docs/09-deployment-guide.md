# 09 — Deployment Guide

## Local development (Docker Compose)

```bash
cp .env.example .env
```

```bash
docker compose up --build
```

| Service | URL / port | Notes |
|---|---|---|
| `web` | http://localhost:3000 | Next.js production build |
| `api` | http://localhost:8000 | FastAPI with reload; docs at `/docs` |
| `db` | 127.0.0.1:5432 | `postgis/postgis:16-3.4` |
| `redis` | 127.0.0.1:6379 | Cache and Celery broker |
| `worker` | — | Celery worker with embedded beat scheduler (hourly session purge) |
| `migrate` | — | Runs `alembic upgrade head` before `api` and `worker` start |

## Running without Docker

Backend (Python 3.12+, PostgreSQL 16 with PostGIS, Redis):

```bash
cd backend && python -m venv .venv && .venv/bin/pip install -e ".[dev]"
```

```bash
cd backend && .venv/bin/alembic upgrade head && .venv/bin/uvicorn app.main:app --reload
```

Frontend (Node 22):

```bash
cd frontend && npm install && npm run dev
```

## Configuration

| Variable | Default | Purpose |
|---|---|---|
| `CIVICWATCH_ENVIRONMENT` | `development` | `development`, `test`, `staging`, `production` |
| `CIVICWATCH_DATABASE_URL` | local `civicwatch` DB | SQLAlchemy URL (`postgresql+psycopg://…`) |
| `CIVICWATCH_REDIS_URL` | `redis://localhost:6379/0` | Redis / Celery broker |
| `CIVICWATCH_CORS_ORIGINS` | `http://localhost:3000` | Comma-separated allowed browser origins |
| `CIVICWATCH_LOG_LEVEL` | `INFO` | Log level |
| `CIVICWATCH_SESSION_COOKIE_NAME` | `__Host-cw_session` | Compose uses `cw_session` for plain-HTTP local development |
| `CIVICWATCH_SESSION_COOKIE_SECURE` | `true` | Must be `true` in staging/production (enforced at start-up) |
| `CIVICWATCH_SESSION_IDLE_TIMEOUT_MINUTES` | `10080` (7 days) | Session ends after this long without activity |
| `CIVICWATCH_SESSION_ABSOLUTE_TIMEOUT_MINUTES` | `43200` (30 days) | Maximum session lifetime |
| `CIVICWATCH_LOGIN_FAILURES_PER_ACCOUNT` | `5` | Failed sign-ins per account per window before lockout |
| `CIVICWATCH_LOGIN_ATTEMPTS_PER_IP` | `30` | Sign-in attempts per IP per window |
| `CIVICWATCH_LOGIN_WINDOW_SECONDS` | `900` | Sign-in rate-limit window |
| `CIVICWATCH_REGISTRATIONS_PER_IP` | `10` | Registrations per IP per window |
| `CIVICWATCH_REGISTRATION_WINDOW_SECONDS` | `3600` | Registration rate-limit window |
| `NEXT_PUBLIC_API_BASE_URL` | `http://localhost:8000/api/v1` | API base URL baked into the frontend build |

## Production

Not yet defined (Milestone 6). Requirements already fixed: HTTPS only, secrets from a secret manager, private object storage, database role without superuser or table ownership for the app (needed for RLS), backups for PostgreSQL, uvicorn behind the proxy with `--proxy-headers --forwarded-allow-ips=<proxy IPs>` so rate limits see real client IPs, and a separate `celery beat` process.
