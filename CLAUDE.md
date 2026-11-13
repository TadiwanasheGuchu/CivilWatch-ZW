# CLAUDE.md — CivicWatch ZW

> Project: CivicWatch ZW  
> Version: 1.0  
> Product: Multi-Council Civic Infrastructure Reporting Platform  
> Architecture: Multi-tenant Modular Monolith  
> Primary Market: Zimbabwe  
> Development Approach: Mobile-first, security-first, production-minded

---

# 1. PROJECT OVERVIEW

CivicWatch ZW is a civic technology platform connecting Zimbabwean residents with local authorities through transparent infrastructure reporting and management.

Residents can report damaged roads, potholes, broken streetlights, drainage problems, waste management issues, water infrastructure problems and other public infrastructure concerns.

Councils can verify reports, assign maintenance teams, track work and analyse infrastructure performance.

The platform supports multiple councils operating independently within one application.

## Product vision

Make public infrastructure reporting accessible, transparent and accountable.

## Core principles

1. Mobile-first user experience.
2. Security and privacy by design.
3. Multi-tenant data isolation.
4. Reliable reporting workflows.
5. Geographic intelligence.
6. Accessible interfaces.
7. Maintainable and testable code.
8. Professional, distinctive visual design.

IMPORTANT: This is not a generic CRUD dashboard. Every feature must support a genuine user workflow.

---

# 2. NON-NEGOTIABLE DEVELOPMENT RULES

Claude must follow these rules throughout development.

## 2.1 Architecture

- Follow the approved architecture in `docs/`.
- Use a modular monolith for the backend.
- Keep frontend and backend separated.
- Use PostgreSQL with PostGIS.
- Use FastAPI for backend APIs.
- Use Next.js App Router and TypeScript.
- Use SQLAlchemy for ORM.
- Use Alembic for migrations.
- Use Docker Compose for local development.
- Use Redis and Celery for background jobs where required.
- Do not introduce microservices prematurely.
- Do not replace agreed technologies without explaining the reason and obtaining approval.

## 2.2 Code quality

- Write production-minded, readable code.
- Avoid unnecessary abstractions.
- Use clear naming conventions.
- Keep components small and reusable.
- Avoid duplicated business logic.
- Keep API route handlers thin.
- Place business logic in service layers.
- Use typed request and response schemas.
- Validate all external inputs.
- Handle errors explicitly.
- Never leave incomplete placeholder implementations in production workflows.
- Do not silently swallow exceptions.
- Avoid oversized files and components.

## 2.3 Development discipline

Before implementing a feature:

1. Inspect the existing project structure.
2. Read relevant documentation.
3. Identify existing implementations.
4. Understand database dependencies.
5. Identify security implications.
6. Create an implementation plan.
7. Implement incrementally.
8. Run relevant tests.
9. Report completed work and remaining issues.

Never rewrite working modules simply because a different implementation is preferred.

Never overwrite existing user work without understanding its purpose.

Do not claim a feature is complete unless it has been implemented and tested.

---

# 3. TECHNOLOGY STACK

## Frontend

- Next.js
- React
- TypeScript
- Tailwind CSS
- shadcn/ui
- Radix UI
- Lucide React
- React Hook Form
- Zod
- TanStack Query
- MapLibre GL JS

## Backend

- Python
- FastAPI
- Pydantic
- SQLAlchemy
- Alembic
- PostgreSQL
- PostGIS
- Redis
- Celery

## Infrastructure

- Docker
- Docker Compose
- Git
- GitHub Actions
- S3-compatible object storage
- Cloud deployment when ready

## Testing

- Pytest
- HTTPX
- Playwright
- Frontend component tests

Do not install alternative libraries without a technical reason.

---

# 4. MOBILE-FIRST DESIGN — CRITICAL

Mobile-first design is mandatory, especially for the resident experience.

CivicWatch serves users who may have:
- Budget Android smartphones.
- Limited mobile data.
- Slow or inconsistent network connections.
- Small screens.
- Older browsers.
- Limited experience with complex digital platforms.

The application must work exceptionally well on smartphones before being expanded for tablets and desktop computers.

## 4.1 Responsive design strategy

Use these design breakpoints as initial guidelines:

- Small mobile: 320px–374px
- Standard mobile: 375px–767px
- Tablet: 768px–1023px
- Desktop: 1024px–1439px
- Large desktop: 1440px+

Do not design desktop layouts first and shrink them for mobile.

Design the mobile experience first, then progressively enhance the interface for larger screens.

## 4.2 Mobile resident experience

The resident interface must provide:

- Simple navigation.
- Large touch targets.
- Easy report submission.
- Camera and gallery photo uploads.
- Mobile-friendly map interactions.
- Clear status tracking.
- Minimal typing.
- Readable typography.
- Accessible form controls.
- Clear loading and error states.

Use a bottom navigation bar where appropriate.

Suggested resident navigation:

- Home
- Explore
- Report
- My Reports
- Profile

The Report action should be visually prominent.

## 4.3 Mobile reporting workflow

The report submission process must be designed for mobile screens.

Recommended steps:

1. Select infrastructure category.
2. Describe the problem.
3. Capture or upload photographs.
4. Select or confirm location.
5. Choose public or private visibility.
6. Review and submit.

Requirements:

- Allow camera capture on supported devices.
- Allow gallery selection.
- Display upload progress.
- Compress large images client-side where appropriate.
- Allow users to retry failed uploads.
- Preserve form drafts locally when appropriate.
- Avoid unnecessarily long forms.
- Use clear validation messages.
- Never lose a completed draft because of a temporary network failure.

Offline drafts are a priority. Full offline submission and background synchronisation can be introduced incrementally.

## 4.4 Mobile performance

- Minimise JavaScript bundles.
- Lazy-load map functionality.
- Optimise photographs.
- Avoid large decorative assets.
- Paginate report lists.
- Avoid loading unnecessary dashboard data.
- Use skeleton states.
- Support slow connections gracefully.
- Avoid unnecessary network requests.

Target a good Core Web Vitals experience on representative mobile devices.

## 4.5 Council staff interfaces

Council dashboards can use desktop-oriented layouts where operational efficiency requires them.

However, they must remain responsive.

Maintenance officers should be able to use smartphones to:

- View assigned reports.
- Navigate to reported locations.
- Upload repair evidence.
- Update work progress.
- Add maintenance notes.

Never make essential workflows desktop-only without a strong reason.

---

# 5. VISUAL IDENTITY AND DESIGN SYSTEM

## 5.1 Brand personality

CivicWatch must feel:

- Trustworthy.
- Professional.
- Modern.
- Clear.
- Approachable.
- Responsible.
- Civic-minded.

Avoid generic AI-generated SaaS aesthetics.

The interface should look like a carefully designed enterprise product.

## 5.2 Colour palette

Use these brand colours consistently.

| Colour | Hex | Usage |
|---|---|---|
| Deep Civic Navy | #172B3A | Primary brand and navigation |
| Civic Teal | #267C72 | Primary actions |
| Soft Mist | #F5F7F8 | Application backgrounds |
| White | #FFFFFF | Surfaces |
| Amber | #E7B45A | Warnings |
| Muted Red | #C65B58 | Errors |
| Slate | #64748B | Secondary text |

Do not introduce additional dominant colours without updating the design system.

Use colour meaningfully and maintain accessible contrast.

## 5.3 Typography

Preferred typography:

- Headings: Manrope
- Body: Inter
- Numeric data: Inter with tabular numerals

Typography should establish clear hierarchy without excessive size differences.

## 5.4 Icons

Use Lucide React.

Requirements:

- Consistent icon sizes.
- Consistent stroke weights.
- Use icons with meaningful labels.
- Avoid mixing unrelated icon libraries.
- Avoid emojis as interface icons.
- Never use decorative icons that confuse functionality.

## 5.5 Visual inspiration

Study the design approaches of:

- Linear: spacing, navigation and interaction details.
- Stripe: polished enterprise layouts.
- Mapbox: geospatial interfaces.
- CivicPlus: public-sector service design.
- GOV.UK: clarity and accessibility.

These are references for design quality, not templates to copy.

## 5.6 Design restrictions

DO NOT use:

- Generic AI dashboard layouts.
- Excessive gradients.
- Glassmorphism everywhere.
- Neon colours.
- Excessive rounded cards.
- Unnecessary animations.
- Random decorative shapes.
- Oversized empty hero sections.
- Excessive shadows.
- Unnecessary charts.
- Placeholder statistics presented as real data.

Avoid making every screen look identical.

Use deliberate visual hierarchy, whitespace, alignment and consistent spacing.

## 5.7 Component consistency

Create reusable components for:

- Buttons.
- Inputs.
- Select fields.
- Status badges.
- Priority badges.
- Tables.
- Cards.
- Modals.
- Drawers.
- Dropdowns.
- Notifications.
- Empty states.
- Loading states.
- Error states.

Do not create a different design implementation for the same component on every page.

---

# 6. APPLICATION USER ROLES

The platform supports:

1. Platform Super Admin.
2. Council Administrator.
3. Department Manager.
4. Verification Officer.
5. Maintenance Officer.
6. Resident.
7. Public Visitor.

Implement role-based access control.

Council permissions must also be restricted by tenant membership.

A user can belong to more than one council, but must only access data belonging to councils where they have valid permissions.

Never rely on frontend role checks alone.

All authorisation must be enforced by the backend.

---

# 7. MULTI-TENANT ARCHITECTURE

CivicWatch uses a shared application and shared PostgreSQL database with logical tenant isolation.

Every council-owned resource must be associated with a council ID.

Examples:

- Departments.
- Memberships.
- Issues.
- Assignments.
- Council-specific settings.
- Audit records.

## Tenant isolation requirements

- Validate council membership on every protected operation.
- Derive tenant permissions from authenticated identity.
- Never trust a council ID supplied by the frontend.
- Enforce tenant restrictions in database queries.
- Implement PostgreSQL Row-Level Security where appropriate.
- Test cross-council access explicitly.
- Prevent accidental data leakage in analytics.
- Keep public and private report visibility separate.

A user from Council A must never access Council B's private reports without explicit authorised membership.

Platform-level access must be tightly controlled and audited.

---

# 8. REPORTING WORKFLOW

Supported infrastructure categories:

- Roads and potholes.
- Streetlights.
- Drainage and flooding.
- Water infrastructure.
- Waste management.
- Public buildings.
- Bridges and pavements.
- Other infrastructure.

## Report statuses

- SUBMITTED
- UNDER_REVIEW
- NEEDS_INFORMATION
- VERIFIED
- ASSIGNED
- IN_PROGRESS
- RESOLVED
- REJECTED
- DUPLICATE
- CLOSED

Every transition must be validated by the backend.

Never allow arbitrary status updates through a generic PATCH endpoint.

Every status transition must create a history record.

## Visibility

Reports support:

- PUBLIC
- PRIVATE

Public reports may be visible to everyone after appropriate moderation.

Private reports are restricted to the resident and authorised council personnel.

Never expose:

- Private resident contact information.
- Private report photographs.
- Private report coordinates.
- Internal council notes.
- Unauthorised comments.

A public report must not become private or vice versa without an authorised visibility-change workflow and audit record.

---

# 9. BACKEND ENGINEERING RULES

Organise FastAPI into independent domain modules.

Recommended modules:

- identity
- councils
- departments
- memberships
- issues
- categories
- evidence
- assignments
- moderation
- workflow
- notifications
- analytics
- audit

Use the following structure:

backend/app/

- api/
- core/
- models/
- schemas/
- repositories/
- services/
- permissions/
- modules/
- workers/

## Backend rules

- Keep route handlers thin.
- Put business logic in services.
- Use repositories where they improve data access organisation.
- Validate using Pydantic.
- Use SQLAlchemy models.
- Use Alembic migrations.
- Use transactions for multi-step operations.
- Use appropriate indexes.
- Handle database exceptions.
- Avoid N+1 queries.
- Use pagination for collections.
- Use structured logging.
- Use consistent API response formats.
- Maintain OpenAPI documentation.

All endpoints must have appropriate authentication and authorisation.

---

# 10. DATABASE ENGINEERING RULES

Use PostgreSQL with PostGIS.

Use UUID primary keys for application entities.

Use timezone-aware timestamps stored in UTC.

Core tables include:

- users
- councils
- council_memberships
- departments
- issue_categories
- issues
- issue_media
- issue_assignments
- issue_updates
- issue_comments
- issue_status_history
- notifications
- audit_logs
- resolution_feedback

## Geospatial requirements

Use PostGIS geography or geometry types with SRID 4326 as appropriate.

Create spatial indexes.

Support:

- Nearby issue searches.
- Council boundary checks.
- Map filtering.
- Geographic clustering.
- Geographic analytics.

Do not calculate geographic proximity using simple string comparisons or arbitrary coordinate approximations.

## Database rules

- Enforce foreign keys.
- Use appropriate uniqueness constraints.
- Create indexes based on query patterns.
- Prevent duplicate memberships.
- Maintain historical records.
- Avoid destructive migrations.
- Never manually edit production data to bypass application rules.

---

# 11. FRONTEND ENGINEERING RULES

Use Next.js App Router.

Recommended structure:

frontend/

- app/
- components/
- features/
- hooks/
- lib/
- services/
- types/
- tests/

Organise features by business domain where practical.

Examples:

features/
- authentication/
- reporting/
- maps/
- council/
- analytics/
- notifications/

## Frontend rules

- Use TypeScript strict mode.
- Avoid `any` unless justified.
- Keep components reusable.
- Separate data fetching from presentation.
- Use TanStack Query for server state.
- Use React Hook Form and Zod for forms.
- Provide accessible controls.
- Handle loading, error and empty states.
- Avoid unnecessary client components.
- Use server components where appropriate.
- Never hardcode production credentials.
- Never use fake data to disguise missing API integration.

For demonstration environments, clearly identify seeded sample data.

---

# 12. API DESIGN

All endpoints must use:

/api/v1

Use REST conventions.

Important endpoint groups:

- /auth
- /users
- /councils
- /departments
- /issues
- /assignments
- /map
- /analytics
- /notifications

## API requirements

- Consistent error responses.
- Input validation.
- Pagination.
- Filtering.
- Sorting.
- Appropriate HTTP status codes.
- Request correlation IDs.
- Rate limiting.
- OpenAPI documentation.

Do not expose internal database models directly as API responses.

Use explicit request and response schemas.

---

# 13. SECURITY REQUIREMENTS

Security is a first-class development requirement.

Implement:

- Argon2id password hashing.
- Secure session management.
- RBAC.
- Tenant isolation.
- PostgreSQL RLS where appropriate.
- CSRF protection when using cookie authentication.
- XSS protection.
- SQL injection protection.
- Rate limiting.
- Secure file uploads.
- Private object storage.
- Short-lived signed URLs.
- Audit logging.
- HTTPS in production.
- Secure secret management.

For uploads:

- Validate actual file content.
- Restrict accepted formats.
- Enforce size limits.
- Scan files where appropriate.
- Strip sensitive EXIF metadata.
- Never expose private object storage directly.

Never:

- Commit secrets.
- Log passwords.
- Log authentication tokens.
- Trust frontend authorisation.
- Allow unauthorised tenant switching.
- Expose private records through analytics.
- Disable security controls to make a demo work.

---

# 14. MAP AND GEOSPATIAL EXPERIENCE

Use MapLibre GL JS.

Use OpenStreetMap-compatible tile sources with appropriate attribution and usage policies.

Map features:

- Infrastructure markers.
- Marker clustering.
- Category filters.
- Status filters.
- Geographic search.
- Report previews.
- Council boundaries.
- Heatmaps.

Mobile map requirements:

- Touch-friendly controls.
- Responsive map panels.
- Easy marker selection.
- Avoid excessive map loading.
- Provide a list alternative to map browsing.
- Ensure the map remains usable on small screens.

Do not make maps the only way to access infrastructure reports.

---

# 15. TESTING REQUIREMENTS

Use:

- Pytest for backend.
- HTTPX for API tests.
- Playwright for end-to-end tests.
- Appropriate frontend component testing tools.

Prioritise:

1. Authentication.
2. Tenant isolation.
3. Public/private visibility.
4. Report submission.
5. Evidence upload.
6. Status transitions.
7. Department assignment.
8. Resolution workflow.
9. Notifications.
10. Analytics permissions.

Mandatory security tests:

- Council A cannot access Council B's private reports.
- Residents cannot modify another resident's private report.
- Unauthorised staff cannot assign reports.
- Private media cannot be publicly accessed.
- Public analytics exclude private report information.
- Invalid status transitions are rejected.

Test mobile layouts at 320px, 375px, 390px and 768px.

Test desktop layouts at 1024px and 1440px.

Never mark a feature complete solely because the page renders.

---

# 16. PERFORMANCE AND ACCESSIBILITY

Target:

- WCAG 2.2 AA.
- Mobile-first responsive layouts.
- Optimised image delivery.
- Lazy loading.
- Paginated data.
- Efficient database queries.
- Keyboard navigation.
- Semantic HTML.
- Clear focus indicators.
- Accessible form labels.
- Meaningful error messages.

Optimise for low-bandwidth environments.

Avoid large initial JavaScript bundles.

Use progressive enhancement wherever practical.

---

# 17. DOCUMENTATION REQUIREMENTS

Maintain these documents:

docs/

- 01-product-requirements.md
- 02-system-architecture.md
- 03-database-design.md
- 04-api-specification.md
- 05-frontend-design-system.md
- 06-security-and-privacy.md
- 07-testing-strategy.md
- 08-development-roadmap.md
- 09-deployment-guide.md

Update documentation whenever an architectural decision changes.

Do not allow documentation to contradict the implementation.

---

# 18. DEVELOPMENT MILESTONES

Implement the application in the following sequence.

## Milestone 1 — Foundation

- Repository setup.
- Docker Compose.
- Next.js setup.
- FastAPI setup.
- PostgreSQL and PostGIS.
- Database migrations.
- Authentication.
- User management.
- Council tenancy.
- Role-based access.

Acceptance: Users can authenticate and access authorised council workspaces. Cross-tenant tests pass.

## Milestone 2 — Reporting

- Infrastructure categories.
- Report submission.
- Photo uploads.
- Map location selection.
- Public/private visibility.
- Resident dashboard.
- Public issue browsing.

Acceptance: Residents can submit and track reports securely.

## Milestone 3 — Council operations

- Council dashboard.
- Report verification.
- Moderation.
- Department management.
- Assignment management.
- Status history.

Acceptance: Council staff can manage reports.

## Milestone 4 — Geographic intelligence

- Map explorer.
- Spatial searches.
- Filters.
- Marker clustering.
- Heatmaps.
- Council boundaries.

Acceptance: Users can explore geographically relevant reports.

## Milestone 5 — Transparency and analytics

- Progress timelines.
- Notifications.
- Resident feedback.
- Performance dashboards.
- Exports.

Acceptance: End-to-end report tracking and analytics work.

## Milestone 6 — Production readiness

- Security review.
- Automated testing.
- Performance optimisation.
- CI/CD.
- Deployment.
- Documentation.
- Demo environment.

Acceptance: A working, secure, documented and publicly accessible portfolio application.

---

# 19. CLAUDE CODE WORKING INSTRUCTIONS

When asked to implement a feature:

1. Inspect the existing repository.
2. Read this CLAUDE.md.
3. Read relevant project documentation.
4. Identify the affected modules.
5. Explain the implementation approach.
6. Identify database changes.
7. Identify API changes.
8. Identify UI changes.
9. Identify security implications.
10. Implement the feature.
11. Run tests.
12. Fix failures.
13. Summarise modified files.
14. Document outstanding work.

For large tasks, break work into manageable stages.

Do not attempt to build the entire application in one enormous operation.

## Prohibited shortcuts

- Fake API implementations.
- Hardcoded dashboard statistics.
- Fake successful authentication.
- Unprotected administrative endpoints.
- Cross-tenant database queries.
- Public permanent URLs for private uploads.
- Arbitrary workflow transitions.
- Incomplete error handling.
- Duplicate component libraries.
- Unnecessary dependencies.
- Placeholder buttons that do nothing.
- Desktop-only resident workflows.

## When encountering uncertainty

Do not invent important business rules.

Explain the uncertainty, propose a sensible default and request clarification when the decision materially affects security, architecture or business behaviour.

## When changing architecture

Explain:

- What is changing.
- Why it is necessary.
- What existing modules are affected.
- Whether database migrations are required.
- What risks are introduced.

Obtain approval before making significant architectural changes.

---

# 20. DEFINITION OF DONE

A feature is complete only when:

- It meets its requirements.
- It works with the actual backend.
- It respects tenant permissions.
- It handles validation and errors.
- It has responsive mobile layouts.
- It is accessible.
- It has relevant automated tests.
- It does not expose private information.
- It is documented where necessary.
- It has been manually verified.

A beautiful interface is not a completed feature if the underlying functionality does not work.

A working backend is not a completed feature if residents cannot use it effectively on a smartphone.

---

# FINAL PROJECT DIRECTIVE

Build CivicWatch ZW as a serious civic technology product.

Prioritise:

1. Correctness over speed.
2. Security over convenience.
3. Mobile usability over desktop-first assumptions.
4. Real functionality over visual demonstrations.
5. Maintainability over unnecessary complexity.
6. Consistent design over generic AI-generated interfaces.

The result should be a professional, production-minded application that demonstrates strong full-stack engineering, thoughtful product design, geospatial capabilities and real-world problem solving.

**Remember: CivicWatch is being built for real people using real devices and real network conditions in Zimbabwe. Design and engineer accordingly.**
