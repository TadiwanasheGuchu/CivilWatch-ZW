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
| `worker` | — | Celery worker |
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
| `NEXT_PUBLIC_API_BASE_URL` | `http://localhost:8000/api/v1` | API base URL baked into the frontend build |

## Production

Not yet defined (Milestone 6). Requirements already fixed: HTTPS only, secrets from a secret manager, private object storage, database role without superuser or table ownership for the app (needed for RLS), backups for PostgreSQL.
