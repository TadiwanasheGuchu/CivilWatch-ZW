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
| `worker` | — | Celery worker with embedded beat scheduler (hourly session purge, notification emails every minute) |
| `mailpit` | http://localhost:8025 | Catches every email sent locally; nothing is delivered to real mailboxes |
| `minio` | 127.0.0.1:9000 (S3), :9001 (console) | Private photo storage; browsers fetch photos here through signed URLs |
| `minio-init` | — | Creates the private bucket and a storage account limited to it, then exits |
| `migrate` | — | Runs `alembic upgrade head` before `api` and `worker` start |

The database container creates `civicwatch_app` (password `APP_DB_PASSWORD` from `.env`) and `civicwatch_worker` (password `WORKER_DB_PASSWORD`) only when its volume is first initialised.

**If your volume is older than stage 5.2**, migration `0011` creates `civicwatch_worker` without a login; give it one (with the password from `.env`) instead of recreating the volume:

```bash
docker compose exec db psql -U civicwatch -c "ALTER ROLE civicwatch_worker LOGIN PASSWORD 'change-me-worker-local-only'"
```
 `.env` also needs the MinIO and storage values from `.env.example` (stage 2.2).

**If you ran the stack before stage 1.3**, recreate the volume so the role exists (this deletes local data):

```bash
docker compose down -v
```

### First platform administrator

Register an account through the API, then on the server:

```bash
docker compose exec api python -m app.cli grant-platform-admin you@example.com
```

`revoke-platform-admin` reverses it. Both are written to the audit log. There is intentionally no HTTP endpoint for this.

### Sample boundaries (demonstrations)

```bash
docker compose exec api python -m app.cli load-sample-boundaries --create-missing
```

This gives Harare, Bulawayo, Mutare, Gweru, Masvingo and Kwekwe **sample** octagon boundaries (creating those councils if needed). They are labelled as samples everywhere; replace them with official GeoJSON through `PUT /api/v1/councils/{id}/boundary`.


## Running without Docker

Backend (Python 3.12+, PostgreSQL 16 with PostGIS, Redis). Create a login role `civicwatch_app` with a password, set both database URLs (see Configuration), then:

```bash
cd backend && python -m venv .venv && .venv/bin/pip install -e ".[dev]"
```

```bash
cd backend && .venv/bin/alembic upgrade head && .venv/bin/uvicorn app.main:app --reload
```

Frontend (Node 22). `npm run dev` and `npm run build` first copy MapLibre's worker into `public/maplibre/` (generated, not committed):

```bash
cd frontend && npm install && npm run dev
```

## Configuration

| Variable | Default | Purpose |
|---|---|---|
| `CIVICWATCH_ENVIRONMENT` | `development` | `development`, `test`, `staging`, `production` |
| `CIVICWATCH_DATABASE_URL` | local `civicwatch` DB | API connection; must use the unprivileged `civicwatch_app` role |
| `CIVICWATCH_MIGRATION_DATABASE_URL` | falls back to `CIVICWATCH_DATABASE_URL` | Schema-owner connection used only by Alembic |
| `CIVICWATCH_WORKER_DATABASE_URL` | unset | Worker connection as `civicwatch_worker`, for email delivery; unset disables email |
| `CIVICWATCH_REDIS_URL` | `redis://localhost:6379/0` | Redis / Celery broker |
| `CIVICWATCH_CORS_ORIGINS` | `http://localhost:3000` | Comma-separated allowed browser origins |
| `CIVICWATCH_LOG_LEVEL` | `INFO` | Log level |
| `CIVICWATCH_SESSION_COOKIE_NAME` | `__Host-cw_session` | Compose uses `cw_session` for plain-HTTP local development |
| `CIVICWATCH_SESSION_COOKIE_SECURE` | `true` | Must be `true` in staging/production (enforced at start-up) |
| `CIVICWATCH_SESSION_IDLE_TIMEOUT_MINUTES` | `10080` (7 days) | Session ends after this long without activity |
| `CIVICWATCH_SESSION_ABSOLUTE_TIMEOUT_MINUTES` | `43200` (30 days) | Maximum session lifetime |
| `CIVICWATCH_STAFF_SESSION_IDLE_TIMEOUT_MINUTES` | `720` (12 hours) | Idle limit for council staff and platform admins |
| `CIVICWATCH_STAFF_SESSION_ABSOLUTE_TIMEOUT_MINUTES` | `10080` (7 days) | Maximum session lifetime for staff |
| `CIVICWATCH_LOGIN_FAILURES_PER_ACCOUNT` | `5` | Failed sign-ins per account per window before lockout |
| `CIVICWATCH_LOGIN_ATTEMPTS_PER_IP` | `30` | Sign-in attempts per IP per window |
| `CIVICWATCH_LOGIN_WINDOW_SECONDS` | `900` | Sign-in rate-limit window |
| `CIVICWATCH_REGISTRATIONS_PER_IP` | `10` | Registrations per IP per window |
| `CIVICWATCH_REGISTRATION_WINDOW_SECONDS` | `3600` | Registration rate-limit window |
| `CIVICWATCH_REPORTS_PER_USER` | `20` | Reports one user may submit per window |
| `CIVICWATCH_REPORT_WINDOW_SECONDS` | `3600` | Report rate-limit window |
| `CIVICWATCH_SERVICE_AREA_BBOX` | `[25.0,-22.6,33.2,-15.4]` | West, south, east, north (WGS 84) that every report must fall inside; default covers Zimbabwe |
| `CIVICWATCH_STORAGE_ENDPOINT_URL` | `http://localhost:9000` | S3 endpoint the API uses (unset for AWS S3) |
| `CIVICWATCH_STORAGE_PUBLIC_ENDPOINT_URL` | same as above | Endpoint photo URLs are signed for — the address browsers reach |
| `CIVICWATCH_STORAGE_BUCKET` | `civicwatch-media` | Must be private |
| `CIVICWATCH_STORAGE_ACCESS_KEY_ID`, `CIVICWATCH_STORAGE_SECRET_ACCESS_KEY` | — | Storage credentials; give them access to this bucket only |
| `CIVICWATCH_STORAGE_REGION` | `us-east-1` | |
| `CIVICWATCH_MEDIA_URL_TTL_SECONDS` | `300` | Lifetime of signed photo URLs (30–3600) |
| `CIVICWATCH_PUBLIC_READS_PER_IP` | `600` | Requests per IP per window to the expensive public endpoints (`CIVICWATCH_PUBLIC_READ_WINDOW_SECONDS`, 300) |
| `CIVICWATCH_PREPARE_DATABASE_ON_START` / `CIVICWATCH_SEED_DEMO_ON_START` | `false` | Hosts without a release step: create roles and migrate, and seed sample data once (`DEMO_ACCOUNT_PASSWORD` required), before serving |
| `CIVICWATCH_EXPORTS_PER_USER` | `20` | CSV exports per user per window (`CIVICWATCH_EXPORT_WINDOW_SECONDS`, 3600) |
| `CIVICWATCH_MAX_REQUEST_BYTES` / `CIVICWATCH_MAX_BOUNDARY_REQUEST_BYTES` | `1048576` / `8388608` | Largest request body; photo uploads use `PHOTO_MAX_UPLOAD_BYTES` |
| `CIVICWATCH_SMTP_HOST` | unset | SMTP server; unset disables email (in-app notifications still work) |
| `CIVICWATCH_SMTP_PORT` | `587` | |
| `CIVICWATCH_SMTP_USERNAME`, `CIVICWATCH_SMTP_PASSWORD` | unset | SMTP credentials (secret) |
| `CIVICWATCH_SMTP_STARTTLS` / `CIVICWATCH_SMTP_USE_SSL` | `true` / `false` | STARTTLS on 587, or implicit TLS on 465; Compose turns both off for Mailpit |
| `CIVICWATCH_EMAIL_FROM` | unset | Sender, e.g. `CivicWatch ZW <notifications@example.org>`; required when `SMTP_HOST` is set |
| `CIVICWATCH_PUBLIC_WEB_URL` | `http://localhost:3000` | Address of the web app, for links in emails |
| `CIVICWATCH_EMAIL_MAX_ATTEMPTS` / `CIVICWATCH_EMAIL_MAX_AGE_HOURS` / `CIVICWATCH_EMAIL_BATCH_SIZE` | `5` / `48` / `50` | Retry limit, oldest notification still emailed, emails per run |
| `CIVICWATCH_PHOTO_MAX_UPLOAD_BYTES` | `10485760` | Largest accepted upload |
| `CIVICWATCH_PHOTOS_PER_ISSUE` | `5` | Photos per report |
| `CIVICWATCH_PHOTO_UPLOADS_PER_USER` | `60` | Uploads per user per window (`CIVICWATCH_PHOTO_UPLOAD_WINDOW_SECONDS`, 3600) |
| `NEXT_PUBLIC_API_BASE_URL` | `http://localhost:8000/api/v1` | API base URL baked into the frontend build |
| `NEXT_PUBLIC_MAP_TILE_URL` | `https://tile.openstreetmap.org/{z}/{x}/{y}.png` | Raster tile template. **Set a tile provider for production**: OpenStreetMap's public tile server forbids heavy app traffic |
| `NEXT_PUBLIC_MAP_ATTRIBUTION` | OpenStreetMap contributors | Attribution required by the tile provider |
| `NEXT_PUBLIC_MEDIA_ORIGINS` | `http://localhost:9000 http://127.0.0.1:9000` | Space-separated origins photos are served from (the storage public endpoint); used by the Content-Security-Policy |
| `API_PROXY_TARGET` | unset | Server-side only: when set, `/api/*` is forwarded to this API address; use with `NEXT_PUBLIC_API_BASE_URL=/api/v1` |
| `NEXT_PUBLIC_DEMO_MODE` | unset | `true` shows the "Demonstration site — sample data" banner on every page |

## Free demo hosting

A public demonstration on free tiers, with no card needed. Each free service has limits (below), so this is for showing the product, not for real councils.

| Part | Service (free tier) | Notes |
|---|---|---|
| Web app | Vercel (Hobby) | Serves the Next.js app and forwards `/api/*` to the API, so the browser sees one site |
| API | Render (Free web service, Docker) | Sleeps after 15 minutes idle; the first request then takes about a minute |
| Database | Neon (Free) with PostGIS | Suspends when idle and wakes in about a second |
| Cache and rate limits | Upstash Redis (Free) | |
| Photos | Backblaze B2 (10 GB free), **private** bucket | Browsers get 5-minute signed links |

Not included on the free plan: **email** (needs a background worker, which Render's free plan does not have; in-app notifications still work) and the hourly session clean-up.

### 1. Database — Neon

1. Create a project (region: Frankfurt, `aws-eu-central-1`, close to Render's Frankfurt region).
2. In the SQL Editor run `CREATE EXTENSION IF NOT EXISTS postgis;` (the migrations also do this, but this confirms PostGIS is available).
3. Copy the connection string for the owner role (`neondb_owner`). Use the **direct** connection, not the pooled one. This is `CIVICWATCH_MIGRATION_DATABASE_URL`.
4. Choose a long random password for the API's role, and write the API's URL as the same string with `civicwatch_app:<that password>` in place of the owner's name and password. This is `CIVICWATCH_DATABASE_URL`. The API creates the role itself on first start (`python -m app.cli prepare-database`).

### 2. Redis — Upstash

Create a Redis database (region: Frankfurt) and copy its `rediss://default:…@…:6379` URL. This is `CIVICWATCH_REDIS_URL`.

### 3. Photos — Backblaze B2

1. Create a bucket with **Files in bucket: Private**.
2. Create an application key limited to that bucket, with read and write access.
3. From the bucket page, note the S3 endpoint (e.g. `s3.us-west-004.backblazeb2.com`). The region is the middle part (`us-west-004`).

### 4. API — Render

1. New → **Blueprint**, pick this repository and branch; Render reads `render.yaml`.
2. Fill in the values it asks for:
   - `DEMO_ACCOUNT_PASSWORD`: the password for the sample accounts (at least 10 characters).
   - The two database URLs and the Redis URL.
   - `CIVICWATCH_CORS_ORIGINS` and `CIVICWATCH_PUBLIC_WEB_URL`: your Vercel address (step 5). You can fill in the expected address now and correct it later.
   - The storage values: endpoint `https://s3.<region>.backblazeb2.com`, the region, bucket, key ID and key.
3. Deploy. On start the service creates the database roles, applies migrations and, once only, adds the labelled sample data. Check `https://<service>.onrender.com/api/v1/health/ready`.

### 5. Web app — Vercel

1. Add New → Project, import the repository, set **Root Directory** to `frontend`.
2. Environment variables:

| Variable | Value |
|---|---|
| `NEXT_PUBLIC_API_BASE_URL` | `/api/v1` |
| `API_PROXY_TARGET` | `https://<service>.onrender.com` |
| `NEXT_PUBLIC_MEDIA_ORIGINS` | `https://s3.<region>.backblazeb2.com` |
| `NEXT_PUBLIC_DEMO_MODE` | `true` |

3. Deploy, then make sure Render's `CIVICWATCH_CORS_ORIGINS` and `CIVICWATCH_PUBLIC_WEB_URL` match the production address Vercel gives you (e.g. `https://civicwatch-zw.vercel.app`). Preview deployments use other addresses and will be refused by the API.

### Using the demo

Sign in with any sample account using `DEMO_ACCOUNT_PASSWORD`:

| Account | What you can see |
|---|---|
| `demo.resident1@example.com` (also `2`, `3`) | My reports, the report form, notifications, "Was it fixed?" |
| `demo.harare.admin@example.com` | The whole Harare workspace: queue, review, assignment, performance, export, staff, audit log |
| `demo.harare.verifier@example.com` | Reviewing and verifying reports |
| `demo.harare.roads.manager@example.com` | Assigning and closing Roads work |
| `demo.harare.officer@example.com` | My work: starting and resolving jobs with repair photos |
| The same four for `bulawayo` | Bulawayo City Council |

The sample platform administrator gets a random password that is never shown, so nobody can create councils or appoint staff on the public demo. To administer it yourself, register your own account and grant it with the operator command from a machine that can reach the database (`CIVICWATCH_MIGRATION_DATABASE_URL` set; Render's free plan has no shell).

### Limits and trade-offs

- The first visit after 15 idle minutes waits for Render to wake (about a minute).
- Anyone you give the demo password to can change the sample data. To reset it, delete and recreate the Neon branch, then restart the Render service: it seeds again.
- Render's address is public, so a client could send its own `X-Forwarded-For` straight to it to dodge per-IP rate limits. Acceptable for a demo; the paid stack (below) only exposes Caddy.
- The map uses OpenStreetMap's public tiles, which allow light use like a demo but not production traffic.

## Production

### What you need

- A Linux server with Docker (2 vCPU and 4 GB RAM is plenty to start), with ports 80 and 443 open.
- A domain whose DNS points at the server (Caddy then gets the TLS certificate itself).
- A **private** S3 bucket (AWS S3 `af-south-1` is the nearest region, or another S3-compatible service) and an access key limited to it. Allow `GET` from your domain in the bucket's CORS settings so browsers can show signed photo URLs.
- Optional: an SMTP account for email, and a raster tile provider (OpenStreetMap's public tile server forbids heavy app traffic).

### 1. Publish images

Set these **repository variables** in GitHub (Settings → Secrets and variables → Actions → Variables): `PUBLIC_API_BASE_URL` (`https://your.domain/api/v1`), `PUBLIC_MEDIA_ORIGINS` (your bucket's origin, e.g. `https://bucket.s3.af-south-1.amazonaws.com`), `PUBLIC_MAP_TILE_URL`, and `PUBLIC_DEMO_MODE` (`true` for the demonstration site). Each push to `main` that passes CI then publishes `ghcr.io/<owner>/<repo>-api:<sha>` and `-web:<sha>` (`.github/workflows/release.yml`). The web image bakes these addresses in, including into its Content-Security-Policy, so changing them means a new build.

### 2. Start the stack

On the server, with a checkout of the repository (for `deploy/` and `docker/db/init/`):

```bash
cp deploy/.env.production.example deploy/.env.production
```

Fill in every value (strong, URL-safe passwords; the image tags you want), then:

```bash
docker compose -f deploy/compose.prod.yml --env-file deploy/.env.production up -d
```

`migrate` applies migrations as the owner role and exits; `api`, `worker` and `beat` (exactly one scheduler) then start. The API refuses to start with unsafe settings (plain-HTTP origins, missing storage credentials, no separate migration URL, email without TLS or the worker role).

### 3. First administrator and (optionally) demo data

Register your own account in the web app, then:

```bash
docker compose -f deploy/compose.prod.yml --env-file deploy/.env.production exec api python -m app.cli grant-platform-admin you@example.org
```

For the public demonstration site only (adds labelled sample councils, staff, residents and reports through the real workflow, and prints the sample accounts' generated passwords once):

```bash
docker compose -f deploy/compose.prod.yml --env-file deploy/.env.production exec api python -m app.cli seed-demo --confirm
```

### Upgrades, backups and logs

- Upgrade: change `API_IMAGE`/`WEB_IMAGE` to the new SHA and run the same `up -d`; `migrate` runs first. Migrations are additive (`docs/03-database-design.md`).
- Back up the `db-data` volume with `pg_dump` from the `db` container on a schedule, keep copies off the server, and test a restore. Photos live in the bucket; enable its versioning.
- Logs are JSON on stdout (`docker compose logs`). Caddy's access log omits query strings, cookies and CSRF headers.

### Regenerating the dependency lock

After changing runtime dependencies in `backend/pyproject.toml`, rebuild `backend/requirements.lock` in a clean Python 3.12 environment:

```bash
python3.12 -m venv /tmp/lock && /tmp/lock/bin/pip install ./backend && /tmp/lock/bin/pip freeze --exclude civicwatch-backend > backend/requirements.lock
```

Restore the two comment lines at the top of the file afterwards.
