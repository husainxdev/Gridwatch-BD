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
