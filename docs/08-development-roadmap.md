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

## Milestone 3 — Council operations

| Stage | Scope | Status |
|---|---|---|
| 3.1 | Workflow rules and transitions, departments, assignment, staff-only notes, council queue and summary, reporter answers to information requests | **Done** (backend) |
| 3.2 | Council screens: dashboard with live counts, queue with filters, report review and actions, assignment, departments, staff departments; maintenance officer "My work" on phones with repair evidence photos | **Done** |

Acceptance: council staff can manage reports. **Met** — Milestone 3 is complete. Next: Milestone 4 (geographic intelligence).

## Later milestones

2. Reporting (in progress):

| Stage | Scope | Status |
|---|---|---|
| 2.1 | Categories, report submission API with location and council checks, own reports, public browsing of verified public reports, status history, RLS | **Done** (backend) |
| 2.2 | Photo evidence: S3-compatible private storage, content validation, EXIF stripping, size limits, short-lived signed URLs | **Done** (backend) |
| 2.3 | Mobile report form (category → description → photos → location → visibility → review) with offline drafts and map location; My reports; public browsing; resident bottom navigation; removing a mistaken photo | **Done** |

Acceptance: residents can submit and track reports securely. **Met** — Milestone 2 is complete. Next: Milestone 3 (council operations).

3. Council operations — dashboard, verification, moderation, departments, assignments, status history.
4. Geographic intelligence — map explorer, spatial search, clustering, heatmaps, boundaries.
5. Transparency and analytics — timelines, notifications, feedback, performance dashboards, exports.
6. Production readiness — security review, performance, CD, deployment, demo environment.
