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
- [x] 9. Admin dashboard and listing controls; search/sort/pagination API.
- [x] 10. Activity conflict check and verified-event history.
- [x] 11. Foundation functional, permission and data-correctness integration tests.
- [x] 12. Initial responsive polish and desktop/mobile browser checks.
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
