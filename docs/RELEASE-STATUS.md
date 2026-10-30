# Sections 13–14 release evidence

**Status: partial; no public deployment has been verified.** The owner is preparing the Vercel/Render dashboards. Actual service origins, provider access, selected plans and authorized external SMTP are not available in this workspace. The latest owner clarification was that hosting is not ready and setup instructions are needed. Follow [the dashboard guide](DASHBOARD_SETUP.md); never send credentials in chat.

## Source and scope

Preparation started from `3ba846c3a19f868476094a638fbec803ac71c72e` on the existing `husainxdev/Gridwatch-BD` main branch. The preparation revision is the Git commit containing this document; obtain the exact immutable SHA with `git rev-parse HEAD`. After a clean commit, `scripts/release-receipt.py` records that full SHA and local test-log checksums in ignored `artifacts/release-receipt.json`. It deliberately leaves live URLs null. A preparation commit is not a deployed revision.

Existing Sections 1–12 capabilities and limitations remain described in [the QA matrix](QA-SECTIONS-11-12.md). This phase preserves Next.js App Router, as explicitly requested earlier, rather than returning to the older Vite specification. No new application schema was needed: head remains `0006`.

## Implemented and locally verified

- Locked Vercel/Render settings, same-origin `/api` proxy, production HTTPS/source-identity/test-build guards and compatible security headers. Provider manifest consistency is a local check, not provider validation.
- Production entry point binds provider `PORT`, runs one worker without reload/access logs, rejects wildcard proxy trust, validates source identity and exposes safe liveness/readiness. Pool limits are configurable (default maximum five connections/process).
- Provider PostgreSQL URL normalization, explicit production TLS mode, exact trusted frontend/CORS origin, strong signing-key guard and separate demo DB namespace.
- One controlled expected-target/advisory-lock migration connection; populated upgrades require an operator backup reference. Real custom-format PostgreSQL backup/isolated restore, checksum validation and refusal of existing/wrong targets.
- Separate private local Admin/User accounts with unique generated passwords, exclusive private credential files and refusal to provision over existing operational records. Real UI login, reload, role navigation and logout were exercised for both accounts. API process restart preserved saved/default data and session behavior.
- Persistent fictional-demo banner, expected disabled-demo empty state, safe release identity route, CI checks, submission/data-source/operations guides, suggested six-minute presentation, viva answers and actual isolated-QA screenshots.

No publicly shared Admin or destructive reset endpoint was introduced. Resetting a practice environment means creating a new isolated namespace, preserving existing databases.

## Commands and actual results

These checks ran against local isolated PostgreSQL 17 and Chromium, with Python 3.12.14, Node 24.19.0 and the committed dependency locks. No production database or real recipient was used.

| Command/check | Actual result | Evidence scope |
| --- | --- | --- |
| `backend/.venv/bin/python scripts/test.py` | **58 passed**, one upstream Starlette/httpx deprecation warning; Alembic detected no missing schema operations | Real isolated PostgreSQL; includes source/restore DBs, corrupted-backup rejection and production-entry-point rejection tests |
| Same runner migration checks | Empty upgrade, disposable downgrade/upgrade, populated `0003 → 0006` preservation passed | Local only; existing user DB not reset |
| `backend/.venv/bin/python scripts/browser-test.py` | **24 passed** in approximately 2.1 minutes | Real local backend/PostgreSQL and production Next build; includes previous core/permission/reset/history/layout journeys and two release checks |
| Private local demo walkthrough | Both generated Admin/User accounts passed UI login, reload, role navigation and logout; browser test helper absent | Local dedicated demo only; not hosted accounts |
| `backend/.venv/bin/ruff check backend scripts` | Passed | Python static checks |
| `backend/.venv/bin/ruff format --check backend scripts` | Passed | Python formatting |
| `npm run format:check --prefix frontend` | Passed | Prettier |
| `npm run lint --prefix frontend` | Passed | Next route type generation and strict TypeScript; not an ESLint claim |
| `npm run build --prefix frontend` | Passed; registered App Router pages generated | Normal production build, no E2E helper flag |
| `npm run check:release --prefix frontend` | **8 cases passed** | Actual Next configuration: HTTPS target, source mismatch, privileged URL, E2E build, rewrite, HSTS and local behavior; no provider contacted |
| `backend/.venv/bin/python scripts/validate-release-config.py` | Passed | Local file/lock/settings consistency only |
| `git diff --check` | Passed | Whitespace/change hygiene |
| Targeted configured-secret/private-demo-password scan | 233 source/static files checked; no matches | Local configured JWT/DB/SMTP secrets and generated private passwords only; not universal secret detection |
| Real HTTPS live smoke/authenticated acceptance | **Not run** | Actual origins/provider access unavailable |
| Remote GitHub Actions | **Not verified** | Local equivalent checks do not establish a remote CI result |

The release guards were additionally checked after the 24-browser run; their positive Vercel branch uses reserved example.com test values only. The normal production build was repeated after the guards changed. Prior viewport/keyboard/axe evidence is linked in the QA matrix. No hosted cookie behavior, physical mobile keyboard, screen-reader certification or native Windows reproduction is claimed.

## Blocked / externally unverified

1. **Hosted connection and journeys:** no verified frontend/backend URLs; no provider deployment, core hosted A–F journey or actual redeploy/persistence result. Read-only `live-smoke.py` is ready but cannot prove write/auth flows by itself.
2. **Provider account properties:** plan cost/entitlement, native runtime patch, pre-deploy/shell access, proxy address policy, SMTP restrictions, cold starts, timeouts and backup retention are unknown. Direct provider docs were restricted by the environment; official source evidence and precise limits are recorded in [PROVIDER_CHECKS.md](PROVIDER_CHECKS.md).
3. **Mail:** SMTP adapter/reset is tested with a controlled local sink. Authorized external sender/credentials and controlled-recipient delivery remain unverified; no delivery claim or exposed reset link.
4. **Real electricity data:** no verified Sylhet pilot/source/feeder mapping or live official API. The isolated fictional fixtures cannot establish real availability or area downtime.
5. **Public operational protection:** limiter is process-local and proxy trust defaults off. Before public launch, verify trusted forwarding, direct-backend exposure and shared ingress protection. Five default DB connections/process is a configuration limit, not a provider-capacity measurement.

## Acceptance

- **Section 13: incomplete.** Release configuration and local recovery checks are implemented; required deployed-site evidence is blocked.
- **Section 14: partially complete.** Documentation, repository directory links, real screenshots, private local demo accounts and presentation/fallback are prepared. Required live links and tested deployed demo credentials are missing.
- **Overall: not fully deployed/submitted; no production-readiness claim.** [SUBMISSION.md](SUBMISSION.md) classifies each deliverable and contains the remaining live checklist. Obtain actual origins/access, review provider costs/limits, configure secrets privately, run the guarded release and verify the real site before changing these statuses.
