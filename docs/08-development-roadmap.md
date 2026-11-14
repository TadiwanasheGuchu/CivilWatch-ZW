# 08 — Development Roadmap

Milestones follow `CLAUDE.md` §18. Each is delivered in small, tested stages.

## Milestone 1 — Foundation

| Stage | Scope | Status |
|---|---|---|
| 1.1 | Repository, docs, Docker Compose, FastAPI core (config, logging, errors, request IDs, security headers, health), Alembic + PostGIS, Celery app, Next.js shell with design tokens, CI | **Done** |
| 1.2 | Users, Argon2id password auth, server-side sessions, CSRF, origin check, rate limiting, own-profile and password change, session purge task | **Done** (backend; UI in 1.4) |
| 1.3 | Councils, memberships, roles, permission layer, RLS with an unprivileged API role, audit log, operator CLI, cross-tenant tests | **Done** (backend; UI in 1.4) |
| 1.4 | Sign-in, registration and account screens; council workspace with switcher, staff management and audit log; shorter staff session limits | **Done** |

Acceptance: users can authenticate and access authorised council workspaces; cross-tenant tests pass. **Met** — Milestone 1 is complete.

## Later milestones

2. Reporting — categories, submission flow with offline drafts, photo upload, map location, visibility, resident dashboard, public browsing.
3. Council operations — dashboard, verification, moderation, departments, assignments, status history.
4. Geographic intelligence — map explorer, spatial search, clustering, heatmaps, boundaries.
5. Transparency and analytics — timelines, notifications, feedback, performance dashboards, exports.
6. Production readiness — security review, performance, CD, deployment, demo environment.
