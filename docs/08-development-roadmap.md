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

## Milestone 4 — Geographic intelligence

| Stage | Scope | Status |
|---|---|---|
| 4.1 | Boundaries (sample loader, upload, validation), locate council, database clustering, public and staff nearby search | **Done** (backend) |
| 4.2 | Explore map (clusters, heatmap, boundaries, filters, preview card), "near me", automatic council choice and similar-report warning in the report form, staff queue map and duplicate suggestions, boundary upload screen | **Done** |

Acceptance: users can explore geographically relevant reports. **Met** — Milestone 4 is complete. Next: Milestone 5 (transparency and analytics).

## Milestone 5 — Transparency and analytics

| Stage | Scope | Status |
|---|---|---|
| 5.1 | In-app notifications (bell, list, read state) for reporters and staff; "Was it fixed?" feedback | **Done** |
| 5.2 | Email notifications (outbox delivery by the worker, opt-out on the account page, Mailpit locally) | **Done** |
| 5.3 | Council performance dashboard, public council progress page with privacy-safe statistics, audited CSV exports | **Done** |
| — | SMS / WhatsApp delivery | Waiting for a decision on channels and providers |

Acceptance: end-to-end report tracking and analytics work. **Met** — Milestone 5 is complete. Next: Milestone 6 (production readiness).

## Milestone 6 — Production readiness

| Stage | Scope | Status |
|---|---|---|
| 6.1 | Security review and hardening: request-size limits, rate limits on public reads and exports, frontend CSP and HSTS, stricter deployed settings, dependency audits | **Done** |
| 6.2 | Production image and stack: locked runtime image, `deploy/compose.prod.yml` with Caddy (HTTPS), separate worker and scheduler, CI image builds, release workflow publishing to GHCR | **Done** — not yet run on a real server |
| 6.3 | Demo environment: `seed-demo` command with labelled sample councils, staff, residents and reports; demo banner | **Done** |
| 6.4 | Free public demo: Vercel (web, with a same-origin API proxy), Render (API, `render.yaml`), Neon (PostGIS), Upstash (Redis), Backblaze B2 (photos); roles, migrations and sample data on start-up | **Ready to deploy** — needs the free accounts (docs/09, "Free demo hosting") |
| 6.5 | Production deployment on a server or paid platform | Later: a server, a domain, a private bucket, an SMTP account and a tile provider |
| — | Performance pass on representative phones (Lighthouse on a throttled connection), backups and restore drill, upload malware scanning, external penetration test | After the first deployment |

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
