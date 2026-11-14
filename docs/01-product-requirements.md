# 01 — Product Requirements

Status: **Living document.** The authoritative product rules are in `CLAUDE.md` §1, §4, §6 and §8; this document records how they are interpreted and any decisions made since.

## Problem

Residents of Zimbabwean towns and cities have no reliable, transparent channel to report failing public infrastructure — potholes, broken streetlights, blocked drains, burst water mains, uncollected waste — or to see whether anything is being done. Councils lack a structured queue to verify, assign and track that work.

## Users

| Role | Scope | Primary device |
|---|---|---|
| Public visitor | Browse moderated public reports | Mobile |
| Resident | Submit and track own reports | Budget Android phone |
| Verification officer | Triage and verify incoming reports for a council | Desktop / mobile |
| Maintenance officer | Work assigned reports in the field, upload repair evidence | Mobile |
| Department manager | Assign and oversee work for a department | Desktop |
| Council administrator | Manage council settings, departments, staff | Desktop |
| Platform super admin | Onboard councils; audited, tightly limited access | Desktop |

A person may hold roles in several councils; every permission is scoped to a council membership.

### Role decisions (stage 1.3)

- **Residents and public visitors are not council roles.** Any signed-in account is a resident; anyone signed out is a public visitor. Council roles (`council_admin`, `department_manager`, `verification_officer`, `maintenance_officer`) are held through `council_memberships`.
- **One active role per person per council.** Someone who needs different duties in two councils holds a separate membership in each. *Open question:* if one person must hold two roles in the *same* council (e.g. verifier and maintenance), this becomes a set of roles per membership.
- **Platform super admins** can create councils and manage council staff (to appoint each council's first administrator), but have **no access to a council's operational data** unless they also hold a membership. They are appointed only from the server command line, never through the API.
- **Staff are added from existing accounts:** a council administrator adds a person by the email of their CivicWatch account. Email invitations for people without an account need an email provider (open question below).
- **A council always keeps at least one administrator.**

## Core journeys

1. **Report** — category → description → photos → location → visibility → review & submit. Drafts survive network loss.
2. **Track** — resident sees every status change of their report and can confirm whether a resolved issue was actually fixed.
3. **Triage** — verification officer reviews, requests information, verifies, rejects or marks duplicates.
4. **Assign & resolve** — manager assigns to a department/officer; officer updates progress and uploads evidence.
5. **Explore** — anyone browses public reports on a map or as a list, filtered by category, status and area.
6. **Analyse** — councils see response and resolution performance; public analytics exclude private reports.

## Infrastructure categories

Roads and potholes · Streetlights · Drainage and flooding · Water infrastructure · Waste management · Public buildings · Bridges and pavements · Other infrastructure.

## Report lifecycle

`SUBMITTED → UNDER_REVIEW → (NEEDS_INFORMATION ↔ UNDER_REVIEW) → VERIFIED → ASSIGNED → IN_PROGRESS → RESOLVED → CLOSED`, with `REJECTED` and `DUPLICATE` as terminal outcomes of review. The exact transition table and which role may perform each transition will be specified in `03-database-design.md` and `04-api-specification.md` when Milestone 3 begins.

## Open questions (need product decisions)

- **Council routing:** is a report routed to a council automatically by point-in-polygon against council boundaries, or does the resident choose? *Proposed default:* automatic by boundary, with manual choice only when the point falls outside every boundary.
- **Moderation of public reports:** are public reports visible immediately or only after verification? *Proposed default:* visible after a verification officer approves them.
- **Anonymous reporting:** must residents have an account to submit? *Proposed default:* yes (account required), to limit abuse and enable tracking.
- **Contact channels:** SMS/WhatsApp notifications vs. email/in-app only. Affects Milestone 5 cost and providers.
