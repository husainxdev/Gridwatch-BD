# Sections 11–12 — local QA and usability validation

Scope: existing Sections 1–10 in the **actual Next.js App Router frontend**, FastAPI and PostgreSQL 17. The phase prompt's Vite/React Router stack line predates the user's explicit Next.js clarification; this phase preserves that approved migration. No public deployment or new product scope is included.

## Baseline and isolation

At `8c45b4a`, the working tree was clean. Baseline: **50 backend tests**, **14 production-browser tests** passed. The existing upstream Starlette/httpx TestClient deprecation warning was non-failing. These results were a starting point, not proof of the new accessibility/email/viewport requirements.

Both runners create UUID-named disposable PostgreSQL databases and drop them in `finally`. They preserve the development database and `.env` files. Test accounts/locations/sources are explicitly fictional; verified status means a simulated review inside that disposable database, not a verified real Sylhet fact. Random record identifiers prevent collisions; time-sensitive numerical expectations use fixed timestamps or existing controlled-clock tests. HTTP journeys use real API persistence; failure tests separately inject identified network/server faults.

The browser runner now overrides SMTP to a dedicated, random-port loopback **in-memory SMTP sink** and clears inherited SMTP credentials/STARTTLS. Reset messages are retrieved by the Node test worker through a loopback HTTP endpoint with access logging disabled. No real external email is sent, no mailbox is shared with users, and the sink is destroyed after the run. Traces, videos and automatic failure screenshots remain disabled. No credentials/reset links are printed. The isolated browser runner uses an auth limit of 500 attempts/minute to accommodate many complete reloads; the default application limit is unchanged and backend controlled-clock rate tests still exercise exhaustion/recovery.

## Requirement / implementation / evidence matrix

| Requirement | Implementation | Verification |
| --- | --- | --- |
| A: signup/login, save/default, reload, logout/relogin | `auth.py`, `security.py`, `Dashboard.tsx`, `session.tsx` | `auth-locations.spec.ts`, `dashboard.spec.ts`: real PostgreSQL persistence and restoration; backend normalized identity/bcrypt cases |
| B: draft privacy, review/publication, revisions/cancellation | `evidence.py`, Admin forms | `evidence.spec.ts`, `planning.spec.ts`; `test_lifecycle_visibility_versions_and_revision`; source link uses actual joined metadata |
| C: A off/retry, B off/back, A still off/back | `submit_report`, per-user episodes, request keys | `qa-failures.spec.ts`: two browser contexts, deliberately lost committed response, same-payload retry, two independent final episodes and latest-person counts; existing moderation/concurrency tests |
| D: saved activity and fresh conflicts after change | `planning.py`, `Planning.tsx` | `planning.spec.ts`: publish → save → cancel → fresh check; backend revision, scope and ownership tests |
| E: private recorded history and independent numbers | `history_calculations`, snapshot history API | `test_qa.py`: persisted complete/open/incomplete records, 10+20 midnight split, clipping, user B excluded; `planning.spec.ts` actual UI summary |
| F: password reset email → reset → revoked sessions → single use | `auth.py`, isolated SMTP sink, reset UI | `qa-reset.spec.ts`: actual SMTP bytes and development reset link, another session invalidated, token replay denied, old password denied/new accepted; backend expiry and simultaneous-use cases |
| JWT/session/role/CSRF/CORS/cookies/rate limits | `security.py`, `auth.py`, `limiting.py` | `test_hardening.py`, `test_planning_admin.py`, `session-tabs.spec.ts`; server denies direct Admin/cross-user calls, expiry/replay/disabled checks, production cookie flags |
| Privacy after logout/account changes | session-keyed components, memory-only credentials/polling cache | `dashboard.spec.ts`, `session-tabs.spec.ts`; private data clears, no auth tokens in browser storage; API `private,no-store` |
| Input/source/query security | strict DTOs, bounded pagination, allowlisted sorts, SQLAlchemy expressions | `test_qa.py` malicious sort/search/source cases; existing hierarchy/UUID/date tests; credential-bearing HTTPS source URLs now rejected |
| Administrative data integrity and audit | transactional locks/versions, constraints, immutable-through-API audit | existing concurrent refresh/report/reset/edit/save/delete tests, invalid trees/references, source revisions; `registry.spec.ts` |
| Planned vs actual, unknown data, demo exclusion, latest user counts | separate schedules/reports/events/episodes; reviewed aggregation | `test_evidence.py`, `test_dashboard.py`, `test_foundation.py`; `qa-failures.spec.ts`; no scheduled restoration or cross-household duration sum |
| 90-minute union / exact boundary / midnight / clipping | half-open UTC intervals, Asia/Dhaka splitting | independent constants in `test_qa.py`; existing contradictory/unknown/open/partial scope cases |
| Migrations and indexed/bounded reads | migrations 0001–0006, composite/Gin indexes, paged APIs | runner empty upgrade, downgrade/re-upgrade, populated 0003→0006 preservation and Alembic model check; bounded benchmark below |
| Responsive and accessibility | existing visual system plus focused fixes | `qa-accessibility.spec.ts`: WCAG-tagged axe checks, no horizontal overflow, keyboard skip/search selection, reduced-height form usability, 360/390/768/1440 widths |
| Slow/unavailable/stale/expired/429/duplicate/empty | abortable fetches, request-key retry, explicit errors and stale labels | `qa-failures.spec.ts`, `cancellation.spec.ts`, controlled-clock polling/network tests and backend 429 tests; no success on a lost response |
| Uploads / external ingestion | Not implemented in the agreed scope | Not applicable; source URLs are stored/displayed, not fetched by the server. No official API or feeder inference claimed. |

## Defects reproduced and changes

| Priority | Reproduction / cause | Fix and regression evidence |
| --- | --- | --- |
| P2 | Axe on 360px home: header/eyebrow/description/footer text had insufficient contrast. Populated Admin location controls also failed destructive-button contrast. | Darkened the existing muted palette and error accent; did not disable contrast rules. All viewport checks include rendered controls. |
| P2 | Activate the skip link: the `main` target was not focusable. Auth pages also used a section heading as their primary heading. | Focusable `main` (`tabIndex=-1`); auth Card uses h1. Keyboard Tab/Enter checks assert actual focus. |
| P2 | Return 503 for public notice API: the error and “no notices” empty state both appeared. No notice retry control was available. | Empty facts require a successful response; loading/error/retry states are distinct. Controlled 503 → real successful retry retains search text. |
| P2 | Schedule list lacked explicit loading/retry states, and fetched its source only after clicking a popup action. Slow source resolution could lose the browser's user-activation window. | Explicit loading/empty/error/retry states. Bounded batch of already-public notice metadata makes the source a normal HTTPS anchor with `noopener noreferrer`, publisher and age. No server-side URL fetching or per-row metadata query. |
| P2 | Two synchronous clicks could enter an action before React committed `busy` state; editing a note after ambiguous delivery appeared to change a pending retry even though the frozen payload was reused. | In-flight ref guards auth/dashboard actions. Pending note is read-only and retry copy states that original time/note are preserved. Lost-response regression verifies only one initial POST, no false success, and identical retry payload/key. |
| P2 | Inspection found unbounded legacy saved-area and personal-episode responses. | Both endpoints now validate page/page_size, cap at 100 and use stable ordering/owner filters. Dashboard and activity picker expose saved paging; moving a default across pages preserves the current viewed area. Regression uses 105 saved areas and 25 episodes; no records are truncated/deleted. |
| P2 | Deleting an old selected saved area while switching to another area could apply the old callback’s selection. | Compare the current area ref after the DELETE resolves. The delayed-response browser regression keeps the newer area selected and confirms paging/default changes do not clear it. |
| P2 | A source such as `https://user:private@example.com/...` passed the HTTPS-only check, placing credentials in a displayed URL. | Reject URL username/password on notice, location verification and registry source DTOs; safe 422 without echoing the credential. No migration needed; existing stored URLs are not silently rewritten. |
| Test harness | A full set of repeated authenticated direct loads exceeded the default 60/min process-local refresh limiter; keyboard assertions could run before hydration; transient success toasts could duplicate. | Test-only rate override, wait for the actual heading before keyboard input, assert completed backend responses instead of treating toast count as persistence. Production limiter not weakened. Backend tests reset process-local buckets between tests so test order cannot exhaust another test’s budget; each test still uses the configured real limit. |

## Engineering usability walkthrough

No participants or satisfaction measurements were invented. The reviewer exercised area search/save/default, notice source/age, off/back reporting, fresh activity conflicts and personal history. Four viewport widths and a reduced 400px viewport emulate keyboard-reduced space; they do not establish physical iOS/Android keyboard behavior. Native browser confirmation/prompt dialogs remain browser-managed; existing action journeys inspect/accept them. There are no custom modal focus traps to certify. Statuses retain words/evidence as well as colors. Reduced-motion CSS exists and remains enabled; no offline operation is claimed.

Screenshots use fictional test accounts only, stored locally as `/tmp/gridwatch-qa-dashboard-{360,390,768,1440}.png` (plus existing history/Admin test captures). No password forms, reset links, mailbox contents or tokens are captured.

## Bounded local performance observation

`test_bounded_schedule_listing_benchmark` uses 1,000 fictional published schedules, one source, 100 records/page, one warm-up and **five requests at concurrency five** through FastAPI TestClient/PostgreSQL in a Linux cloud container (5 logical CPUs). Query count is three/request: count, page, batched source metadata. The run recorded **15 SQL queries**, individual latency **102.26, 76.19, 67.87, 73.13, 99.27 ms**, mean **83.74 ms**, maximum **102.26 ms**. This shared QA container may also run other tests. This is a small local observation with no network/ingress, not a production capacity or percentile guarantee. The fixture is removed before other tests continue.

## Final commands and results

After fixes (baseline/investigation rounds are distinct):

| Command / check | Actual result |
| --- | --- |
| `python3 scripts/test.py` | **54 passed**, one non-failing upstream deprecation warning; fresh empty migration, downgrade/re-upgrade, populated 0003→0006 preservation and model/schema check passed. Polling regression also asserts old observation/start timestamps remain unchanged. |
| `CHROMIUM_EXECUTABLE=/usr/bin/chromium python3 scripts/browser-test.py` | **22 passed** against production Next.js + real FastAPI/PostgreSQL, including all four viewport checks and SMTP journey. |
| `GRIDWATCH_BROWSER_MODE=development CHROMIUM_EXECUTABLE=/usr/bin/chromium python3 scripts/browser-test.py cancellation.spec.ts qa-failures.spec.ts qa-reset.spec.ts` | **4 passed** with Strict Mode enabled; no unhandled cancellation rejection in this environment. |
| `CHROMIUM_EXECUTABLE=/usr/bin/chromium python3 scripts/browser-test.py dashboard.spec.ts qa-pagination.spec.ts --grep 'saved default\|large saved'` | **4 passed** after the final delayed-delete selection guard; includes desktop/mobile defaults, unavailable default fallback and large-collection race. |
| `npm run lint --prefix frontend` | **Passed**: Next route type generation + strict TypeScript/unused checks; no ESLint claim. |
| `npm run format:check --prefix frontend` | **Passed**: Prettier check of application/config/e2e files. |
| `backend/.venv/bin/ruff check backend scripts` / `format --check backend scripts` | **Passed**: Python lint and formatting checks. |
| `npm run build --prefix frontend` | **Passed**: normal Next.js optimized build, separate from the test-hook build; normal production shell 200, test bridge absent and missing route 404. |
| `npm audit --prefix frontend --audit-level=high` | Zero reported vulnerabilities. |
| `uv tool run pip-audit --path backend/.venv/lib/python3.12/site-packages --skip-editable` (temporary tool/cache directories) | No known vulnerabilities found. No package upgrades were required for this phase; axe was added as a dev-only audit tool. |
| Development `alembic current` / `alembic check` | **0006 (head)**, no model drift. No new migration required. |
| Known-secret scan of tracked source + generated static JS/JSON/HTML/map files | **166 files checked**, no matches for the configured local JWT/database/SMTP secrets; no `.env` tracked. This is a targeted check, not a claim to detect every possible secret format. |
| `git diff --check` | **Passed**: whitespace check. |

Axe covers tagged WCAG 2 A/AA, 2.1 AA and 2.2 AA rules across six public and ten authenticated/Admin routes at each width, plus populated dashboards; keyboard and reduced-height checks supplement it. No accessibility rule or validation was disabled. Screenshots at all four widths were visually inspected; tablet evidence cards were changed to one column for readable text.

**Local completion:** Sections 11–12 meet the agreed core definition of done in the tested Linux Chromium/PostgreSQL environment: no known unresolved P0/P1 in that scope. External/browser-specific uncertainties listed below remain explicit. Passing tests does not certify production readiness or full accessibility.

## Remaining boundaries

- No independently verified real Sylhet pilot/provider/notice/feeder dataset. All QA evidence is fictional and isolated. Registry review does not create electrical coverage or an official integration.
- No hosted-domain TLS/cookie/CSRF smoke tests, real external SMTP delivery, backup restoration or public ingress rate controls. The SMTP test covers the application's real adapter against the local controlled sink only.
- Browser automation uses Linux Chromium. Native Windows, Safari/Firefox, physical mobile keyboard and a screen-reader session are not independently verified; automated axe success is not accessibility certification.
- The reported Windows `AbortError` development log has not been reproduced here. The development cancellation regression verifies actual aborted requests without unhandled rejections. The supplied hydration diff contained the extra `wotdisconnected` attribute, which repository code does not render; no suppression was added to application markup. The user's extension-free Windows confirmation remains outstanding (environment-specific, not a reproduced application P0/P1).
- Authentication rate limiting remains process-local. Multiple backend instances require shared ingress protection. History is incomplete personal reporting, not area reliability, continuous monitoring or SAIDI/SAIFI. Bounded API selection limits remain documented.

Sections 13–14 require an agreed host/domain, production database and secret management, SMTP credentials/delivery verification, source verification, backups/restore testing, shared ingress protection and a separate live verification/submission pass. This phase does not authorize public deployment.

## API / setup changes

No schema migration or new external credential is needed. `npm ci --prefix frontend` installs the added **development-only** axe browser auditor. Normal startup commands and the existing PostgreSQL port remain unchanged. Browser tests always override mail configuration with the disposable sink, regardless of a developer’s SMTP settings.

- `GET /api/saved-areas`: `page>=1`, `page_size=1..100` (default 100), returns `items,total,page,page_size`. Stable default-first/name/ID ordering. Default remains on page one. The frontend provides saved-area paging on Dashboard and Activity forms; search/cascading selection remains independent of saved-area pages.
- `GET /api/me/episodes`: same bounds, default size 20, latest observation then UUID. Legacy `items` is retained; collection metadata is added. Use `/api/history` for date-filtered summaries.
- Public schedule list includes a bounded batch of source metadata under `notice` (`source_url,publisher,published_at,updated_at`). Public visibility filters remain unchanged.
- Source submission now requires HTTPS with no URL username/password. Original observations, audits, private records and existing sources are preserved.
