# Progress and proposed seven-day sequence

Checked items are implemented locally. Days are a priority guide, not a deadline guarantee.

- [x] 1. Scope, source verification gate and user flows documented.
- [ ] 1a. Verify one real Sylhet pilot boundary, provider and original official source.
- [x] 2. PostgreSQL models, Alembic migration, health API, demo seed and Bengali UI foundations.
- [x] 3. Registration/login, JWT access, rotating refresh, bcrypt, logout and SMTP password reset.
- [x] 4. Admin/User permissions, validated location tree and saved-area APIs.
- [x] 5. Notice and schedule CRUD, source links and verification states.
- [x] 6. Per-connection reports, request idempotency and duplicate cooldown.
- [x] 7. User dashboard and saved areas.
- [x] 8. Community report list and evidence/uncertainty display.
- [x] 9. Integrated Admin workspace, URL-backed server listings, version checks and transactional audit.
- [x] 10. Saved private activities, fresh announcement conflict checks and recorded personal history.
- [x] 11. Core journeys, permissions, calculations and migration verification against isolated PostgreSQL; see QA report for scope and external exceptions.
- [x] 12. Reproduced fixes, four viewport sizes, automated accessibility/keyboard and failure-state checks; physical devices/screen readers remain unverified.
- [ ] 13. Hosted deployment and live verification; no deployment target or credentials supplied.
- [x] 14a. Setup, architecture and submission-oriented documentation; local account creation instructions.
- [ ] 14b. Verified pilot evidence, real demo content, screenshots and final presentation.

| Suggested day | Focus | Exit evidence |
| --- | --- | --- |
| 1 | Scope, pilot research, foundations | Migration and clear research gate |
| 2 | Auth and permissions | Registration/login/logout/reset and denial tests |
| 3 | Locations, notices, schedules | Validated CRUD and source evidence |
| 4 | Reports and user dashboard | Duplicate handling, saved areas, unknown status |
| 5 | Community evidence and admin controls | Honest summaries and paged lists |
| 6 | Conflicts, history, usability | Overlap tests, keyboard and mobile checks |
| 7 | Hosted deployment and submission | Live smoke tests and verified pilot |

Outstanding risk: actual pilot location/provider data and published notice sources have not been verified. Until then the operational database is intentionally empty after setup and the home screen uses labeled fictional fixtures. Public deployment also needs ingress rate limiting, independent security review, backups and live verification.

## Sections 3–4 verification scope

- [x] Strict signup schema, normalized identity uniqueness and bcrypt byte boundaries.
- [x] Hashed rotating/revocable sessions, concurrency/reuse policy and immediate access revocation.
- [x] Single-use password reset, SMTP/Mailpit adapters, trusted links and generic responses.
- [x] Explicit CORS/CSRF, secure deployment cookies and configurable process-local rate limits.
- [x] Location roots/children/details/ancestors/search, subtree validation and normalized uniqueness.
- [x] Real frontend cascade/search, session restoration and current-user saved areas.
- [x] Migration 0002 and 27 isolated PostgreSQL integration tests.
- [x] Desktop/mobile Chromium integration journeys, including delayed 401 single-refresh handling.
- [ ] Production SMTP delivery and hosted-domain cookie verification (credentials/domain unavailable).

See [the phase guide](AUTH-LOCATIONS.md) for commands, manual checks and known deployment limitations. Earlier checked sections describe existing local capabilities, not production certification.

## Sections 5–6 current phase

- [x] Draft/published/withdrawn/archive notice lifecycle and public privacy gates.
- [x] Schedule publication, cancellation, explicit coverage snapshots, optimistic versions and audit revisions.
- [x] Personal episodes, exact retry validation, concurrent duplicate safety and per-user database limits.
- [x] Latest-observation evidence, moderation and personal history integration.
- [x] Isolated PostgreSQL phase tests and frontend integration.

See [phase scope, API contracts and limitations](SECTIONS-5-6.md). Earlier checklist entries for later sections are historical; this phase does not certify Sections 7–14 as complete.

## Sections 7–8 current phase

- [x] Real dashboard snapshot and explicit selected-area context.
- [x] Saved-area quick switching, optional labels and one persisted default with concurrency/ownership enforcement.
- [x] Today/upcoming/cancelled/revised windows, joined source metadata and snapshot-based partial coverage.
- [x] Latest-per-reporter backend aggregation and independent personal episode/timer.
- [x] Shared polling with cancellation, hidden/offline pause, backoff and stale-data labels.
- [x] Migration 0004, populated-upgrade checks and focused backend/browser validation.

See [phase API and freshness rules](SECTIONS-7-8.md). This phase covers Sections 7–8 and necessary prerequisites; it does not certify Sections 9–14.

## Sections 9–10 current phase

- [x] Admin overview, integrated existing forms, server-side filters/sort/pagination and shareable URL state.
- [x] Versioned safe actions, evidence-preserving cancellation/archive and immutable-through-API audit views.
- [x] Report context, reviewed event association/unassociation and independent personal histories.
- [x] Owned saved activities, half-open/union conflict calculations, fresh results after revision/cancellation.
- [x] Personal episode history, range clipping, Bangladesh-midnight splitting and explicit unknown/review states.
- [x] Migrations 0005–0006, isolated PostgreSQL tests, desktop/mobile browser journey and build checks.
- [x] Source-backed electricity-office/feeder-claim CRUD, review, invalidation, audit and reference preservation.
- [ ] Externally verified real Sylhet pilot/office/feeder data (not supplied; no invented records seeded).

See [API contracts, counting rules, limits and startup instructions](SECTIONS-9-10.md). This phase implements Sections 9–10 for supported entities. Historical checked entries for Sections 11–14 do not mean their full requested phases or hosted deployment are complete.

## Requested stack update and implementation review

- [x] Next.js App Router replaces Vite/React Router; React, TypeScript/JavaScript and Tailwind retained.
- [x] Cross-tab session coordination, exact expiry checks, repeated-restoration fixes and reference-safe concurrent location deletion.
- [x] Review findings and limitations recorded in [the review](REVIEW-2026-10-29.md).
- [ ] Hosted Next.js/API deployment and external SMTP delivery verification.

## Sections 11–12 verification

- [x] 54 backend tests, 22 production browser journeys and four focused development-mode journeys.
- [x] Independent interval/history constants, bounded query benchmark, saved/history collection pagination.
- [x] Axe checks at 360/390/768/1440px, keyboard area selection, skip focus and reduced-height forms.
- [x] Real SMTP adapter to a dedicated loopback sink: reset, single use, old-session invalidation; no external mail.
- [x] Contrast, false empty states, retry controls, duplicate actions, credential-bearing sources and source-link usability fixed.
- [ ] Native Windows/browser-extension reproduction, physical mobile keyboards and screen-reader session (not locally available).

See [verification matrix and QA handoff](QA-SECTIONS-11-12.md). Sections 13–14 deployment/submission remain separate; no public deployment was performed.
