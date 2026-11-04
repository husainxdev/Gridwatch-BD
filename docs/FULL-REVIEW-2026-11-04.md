# Full application follow-up — 2026-11-04

The owner requested work across design, User/Admin workflows, real Sylhet data and deployment. This review started from `447e54b` with a clean working tree. It preserves Next.js/React/TypeScript/Tailwind/DaisyUI, FastAPI, PostgreSQL and existing records. Local functionality and external release readiness remain separate.

## Reproduced gaps and changes

| Priority / origin | Reproduction or missing behavior | Change and verification |
| --- | --- | --- |
| P1, existing backend | With a valid one-connection pool, authenticated Dashboard/History held the auth connection while borrowing a second snapshot connection; both returned 503 | Capture the authenticated UUID, release the read-only auth transaction, then borrow one repeatable-read snapshot. Both new regression cases failed before the fix and pass afterward. Ownership and concurrent-history consistency tests still pass. |
| P1/P2, existing UI | Home always displayed old sample-area placeholders and empty schedule/report cards even when operational records existed | Home now reads a bounded public area snapshot and published notices from the real backend. It has location search/cascade, source/times, community evidence, cancelled schedules, pagination and recent privacy-filtered observations. It never derives power availability from a schedule or missing reports. |
| P1/P2, found while integrating this change | Anonymous session failure cleared the shared polling store, leaving an empty home after data loaded | Account-owned cache still clears on logout/switch; the public evidence namespace survives. Explicit cleanup-event regression, anonymous failure/retry, private two-tab/account-change and stale-data tests verify the separation. |
| P2, existing missing flow | Opening an authenticated route lost its requested page/area after login/signup | Preserve an allowlisted internal path/query through guards, login and registration. Reject external URLs, double slashes, backslashes, control characters and auth/reset loops. Backend permissions still enforce Admin/ownership. |
| P2, existing UX | History opened without the user's saved default and required repeating the hierarchy selection | Restore a valid default once, provide saved-area paging and retain manual/URL selections. Never replace a deliberate selection with a late default response. Account remounting still clears private state. |
| P2, prior demo limitation | Demo reset returned 503 because SMTP was intentionally empty | Launcher enables only the existing local Compose Mailpit loopback binding, clears inherited SMTP credentials and refuses remote/public bindings. A real controlled SMTP message is retrieved privately; browser reset is single-use and revokes the old session. This is not external inbox delivery. |
| P2, introduced/found during this UI work | Long names overflowed at mobile widths; an outlined hover button failed contrast | Wrap breadcrumb/search names and headings, constrain controls, set explicit accessible button colors without color-fade ambiguity. Axe/overflow tests at 360/390/768/1440 pass without disabling rules. |
| P2, existing copy | Sources/Progress still described an early foundation build; reset feedback was English | Describe actual capabilities and remaining release gates, add clear workflow entry points, use conditional Bengali reset feedback without claiming delivery. |

New public response construction never includes private notes, user IDs, idempotency keys, personal episodes/history, sessions or author foreign keys. Source URLs remain validated HTTPS inputs; no arbitrary server-side source fetching was added. No schema change was needed: Alembic head is `0006`.

## Requirement-to-evidence coverage

| Scope | Verified locally | Remaining boundary |
| --- | --- | --- |
| Sections 1–2 | Source rules, architecture, PostgreSQL models, migrations, configuration and startup | Real pilot source verification remains open |
| Sections 3–4 | Auth/session/reset, roles, ownership, hierarchy, saved/default areas; real loopback Mailpit reset added | External sender/delivery and hosted-domain behavior unverified |
| Sections 5–6 | Source-reviewed draft/publication/revision/cancellation, independent reports, retries/moderation/audit | No official live feed or verified real outage facts imported |
| Sections 7–8 | Private dashboard, public home, independent latest-report aggregation, cache/stale/area-change behavior | Self-reports do not establish continuous area monitoring |
| Sections 9–10 | Admin CRUD/filter/sort/paging, source registry, owned activities/conflicts and private history; small-pool fix | Automatic feeder-to-schedule integration remains outside the implemented scope |
| Sections 11–12 | Full backend/browser regressions, privacy/permission/math, four rendered widths, keyboard/axe, production/development modes | Physical devices, other browser engines and screen-reader certification unverified |
| Sections 13–14 | Release/backup tools, private local demo accounts, submission/demo docs and actual UI captures | Actual live origins/accounts, external SMTP, live persistence/backup and hosted acceptance remain blocked |

## Exact checks and results

All destructive test cleanup is restricted to UUID-named test databases. Existing normal/demo databases and `.env` files were preserved. No real recipient received mail.

| Command/check | Actual result |
| --- | --- |
| `backend/.venv/bin/python scripts/test.py` | **63 passed**, one existing Starlette/httpx deprecation warning; fresh/populated migration checks and no schema drift |
| Before the pool fix: `backend/.venv/bin/python scripts/test.py tests/test_public_overview.py -k one_connection` | **Two failures reproduced**, Dashboard and History 503; the full suite subsequently verifies both 200 with no connection left checked out |
| `CHROMIUM_EXECUTABLE=/usr/bin/chromium backend/.venv/bin/python scripts/browser-test.py` | **26 passed**, three dedicated local-demo tests skipped here |
| `GRIDWATCH_BROWSER_MODE=development CHROMIUM_EXECUTABLE=/usr/bin/chromium backend/.venv/bin/python scripts/browser-test.py cancellation.spec.ts public-home.spec.ts` | **Three passed**: pending cancellation, public evidence/failure behavior and safe return navigation |
| Private launcher on a new isolated profile, then dedicated `populated-demo.spec.ts demo-mail.spec.ts` with private file/loopback mailbox selectors | **Three passed**, two populated role/UI journeys plus actual Mailpit reset; no test bridge enabled in that demo |
| `npm run lint --prefix frontend` | Passed: Next route type generation and strict TypeScript/unused checks |
| `npm run format:check --prefix frontend` | Passed: Prettier |
| `npm run build --prefix frontend` | Passed: normal optimized Next build |
| `npm run check:release --prefix frontend` | Ten cases passed |
| `backend/.venv/bin/ruff check backend scripts`, `backend/.venv/bin/ruff format --check backend scripts`, `git diff --check` | Passed |
| Targeted configured-secret/static-output scan | 248 source/static files checked; no configured DB/JWT/SMTP value or private generated demo password matched. This is not universal secret detection; the public screenshots were also visually inspected. |

The normal browser run skips the three dedicated demo cases because they need their own server/database; those cases were actually executed separately. Earlier intermediate failures included a SavedPager prop/type error and overly broad test locators matching Next's route announcer; both were corrected. No validation, permission check or accessibility rule was removed. Browser/SMTP evidence is local Linux Chromium, not a hosted or complete native Windows certification.

Actual anonymous home captures, with explicitly fictional data and no credentials: [mobile](screenshots/home-public-mobile.png), [desktop](screenshots/home-public-desktop.png).

## Real-source research and network gate

The owner explicitly authorized autonomous research/import. No further permission is needed to research public official material. Access is the current constraint:

- On 2026-11-04 both canonical and `www` Sylhet district/BPDB roots returned 503; BPDB's proxy error identified upstream certificate verification failure. SCC roots returned 403 (error 1010). TLS verification was kept enabled. No official content was obtained/imported from these errors.
- A **saved, not applied** network draft preserves the six existing government hosts and adds public search/national portal/BBS/REB/Power Division/division/upazila/PBS candidate hosts and government document hosts. A hostname is a research destination, not a verified record or citation.
- New candidates: `www.google.com`, `bangladesh.gov.bd`, `www.bangladesh.gov.bd`, `bbs.gov.bd`, `www.bbs.gov.bd`, `reb.gov.bd`, `www.reb.gov.bd`, `powerdivision.gov.bd`, `www.powerdivision.gov.bd`, `sylhetdiv.gov.bd`, `sylhetsadar.sylhet.gov.bd`, `pbs1.sylhet.gov.bd`, `pbs2.sylhet.gov.bd`, `portal.gov.bd`, `*.portal.gov.bd`.
- Platform review/save/publication is required before those destinations become active. Active runtime policy was still the six original hosts at the final check. A draft save does not establish reachability or official-data verification.

After activation: discover the original source, verify administrative type/parent and provider independently, retain exact URL/date/evidence, import only the supported facts through the existing Admin workflow, then validate coverage against an original notice. Do not infer feeder coverage or publish fabricated schedules to fill the UI. No real Sylhet hierarchy/notice was silently substituted with the demo fixture.

## Completion boundary

The independently actionable local changes above are implemented and checked. Real-source import and hosted release remain incomplete. No verified live URL, external email delivery, production capacity or fully completed project is claimed. Existing provider/release instructions remain available; this pass did not purchase a service, change repository visibility or deploy publicly.
