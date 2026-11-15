# CivicWatch ZW

A multi-council civic infrastructure reporting platform for Zimbabwe. Residents report potholes, broken streetlights, blocked drains, water leaks and waste problems; councils verify, assign and resolve them in the open.

> **Status:** Milestones 1–4 are complete. Residents report problems from their phones (photos, map pin with automatic council choice, offline drafts) and follow them to resolution; anyone can browse verified public reports as a list or a clustered map with a heatmap and "near me"; council staff review, verify, assign and resolve reports with repair photos, spot nearby duplicates and see their queue on a map, within strict per-council isolation. Next: transparency and analytics (Milestone 5). See [`docs/08-development-roadmap.md`](docs/08-development-roadmap.md).

## Stack

FastAPI · SQLAlchemy · Alembic · PostgreSQL 16 + PostGIS · Redis · Celery · Next.js (App Router) · TypeScript · Tailwind CSS · TanStack Query · Playwright

## Quick start

```bash
cp .env.example .env
```

```bash
docker compose up --build
```

- Web: http://localhost:3000
- API docs: http://localhost:8000/docs
- Readiness: http://localhost:8000/api/v1/health/ready

To run without Docker, and for every configuration variable, see [`docs/09-deployment-guide.md`](docs/09-deployment-guide.md).

## Tests

```bash
cd backend && pytest
```

```bash
cd frontend && npm test && npm run test:e2e
```

## Documentation

Engineering rules for contributors (human or AI) are in [`CLAUDE.md`](CLAUDE.md). Design documents live in [`docs/`](docs/).
