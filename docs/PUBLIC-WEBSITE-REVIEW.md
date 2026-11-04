# Public website presentation and normal startup — 2026-11-04

The owner requested a normal publishable website interface, removing the demo-first workflow. This change preserves the existing Next.js/React/TypeScript/Tailwind/DaisyUI and FastAPI/PostgreSQL architecture, existing accounts/records/configuration and database schema `0006`. It does not deploy publicly, invent real electricity data, or relabel fictional observations as real.

## Implemented

- Public navigation, footer, metadata and icon; no student-project, demo-version or progress-checklist branding on the normal site. Legacy `/progress` renders the practical help page for old links.
- Redesigned green home, source/uncertainty context, immediate area selection before secondary workflow shortcuts and links to working account/report/planning/history journeys. Actual public data still comes from backend endpoints.
- Mobile primary navigation and an accessible expandable secondary menu. Link activation closes it; Escape closes it and returns focus to its button. Desktop retains the full navigation and role-specific Admin entry.
- Real `/help` steps/keyboard-operated FAQ and `/privacy` describing actual public/private fields, required session cookies and current retention/deletion limitations. No invented contact, uptime or coverage claim.
- Bengali administrative type labels, sensible location controls, no useless first-page pagination, honest empty/failure states and retry. Password visibility toggle, autocomplete/input hints, byte-limit help, disabled logout while pending, real backend success/failure feedback.
- `START-WEBSITE.cmd` / `scripts/start-website.py`: normal local DB/schema check and both servers in one terminal. Never seeds accounts/records, never turns a demo DB into a normal DB, preserves secrets/custom ports, handles Desktop startup and process cleanup, keeps logs private and uses separate `.next-website` output.
- Initialization/setup now defaults to no demo and does not invoke a seed. Older `.env` files are preserved; normal launcher forces fixture/helper flags off at runtime. Legacy sample endpoint is accessible only on an explicitly isolated development/test demo instance.
- Public production rejects backend demo flags and Vercel rejects public demo/test/local build flags. Explicit development fixtures and their warnings remain available only for developer regression work; old databases are not erased.

## Verification

All backend/browser fixtures use isolated PostgreSQL databases with controlled identities/mail sinks. Normal-site visual inspection is anonymous; no real user email, password, token or cookie appears in screenshots. No public report or external email was sent.

| Command/check | Observed result |
| --- | --- |
| Baseline `backend/.venv/bin/python scripts/test.py` | 63 passed; one upstream Starlette/httpx deprecation warning |
| Final `backend/.venv/bin/python scripts/test.py` | **71 passed**, same single warning, no schema drift; fresh and populated migration checks passed |
| `CHROMIUM_EXECUTABLE=/usr/bin/chromium backend/.venv/bin/python scripts/browser-test.py` | **28 passed**, **3 skipped**, approximately 2.7 minutes. Skips are dedicated historical isolated-demo cases, not normal website journeys. Real backend/PostgreSQL auth, ownership, saved/default, Admin publication, reports, conflicts/history, reset and account-switch checks passed. |
| Focused `... scripts/browser-test.py public-website.spec.ts public-home.spec.ts` | Four passed before the final full suite; public evidence/privacy, safe redirects, normal branding, menu/FAQ/password toggle and location error/retry |
| `GRIDWATCH_BROWSER_MODE=development CHROMIUM_EXECUTABLE=/usr/bin/chromium backend/.venv/bin/python scripts/browser-test.py cancellation.spec.ts public-website.spec.ts` | **Three passed** in 12.1 seconds; pending-request cancellation and the new public UI in Next development mode |
| `npm run lint --prefix frontend` | Passed: Next route generation and strict TypeScript/unused checks; no ESLint claim |
| `npm run format:check --prefix frontend` | Passed |
| `npm run build --prefix frontend` | Passed, optimized Next build includes help/privacy/icon routes |
| `npm run check:release --prefix frontend` | **13 configuration cases passed**, including demo/test/local-build rejection; no provider contacted |
| `backend/.venv/bin/ruff check backend scripts`, `... ruff format --check backend scripts`, `git diff --check` | Passed |
| `backend/.venv/bin/python scripts/validate-release-config.py` | Passed; local manifest consistency only |
| `backend/.venv/bin/python scripts/start-website.py --check-only` | Passed against the configured normal local database; no fixture provisioning |
| `backend/.venv/bin/python scripts/start-website.py --no-browser` | Actual API+Next dev started at localhost:5173, normal mode, legacy demo API 404, no demo banner or page exceptions |
| Actual normal-page screenshots and overflow checks | 390/1440px captured and visually reviewed; no horizontal page overflow; no invented electricity records |
| Full browser accessibility suite | 360/390/768/1440px core screens; help/privacy also checked at each width with axe WCAG A/AA rules. Physical devices and screen-reader certification unverified. |
| Manual mobile keyboard Escape check | Menu collapsed and focus returned to its toggle |
| Targeted configured-secret/static-output scan | 268 source/static files, no configured DB/JWT/SMTP secret or generated private password matched; bounded check, not universal secret detection |

Screenshots: [390px](screenshots/website-home-390.png), [1440px](screenshots/website-home-1440.png). They show the real empty normal database, not fictional data dressed as a live service. Existing older screenshots/test counts are historical.

## Manual owner check

1. Stop earlier API/web terminals, update and run `START-WEBSITE.cmd`; open http://localhost:5173.
2. Confirm no demo banner, fictional auto-selection or prefilled credentials. Open help/privacy and use the mobile menu.
3. Register your own User; save a genuinely supported area when verified records exist. Reload, log out and verify private routes require login.
4. Create your own Admin using the hidden CLI prompt described in [WEBSITE.md](WEBSITE.md); publish only source-supported area/notice/schedule facts, then inspect them anonymously.
5. Test reset through local Mailpit; public email delivery requires a configured real sender and separate controlled-recipient verification.

## Remaining public-launch requirements

No independently verified real Sylhet area/notice/feeder mapping or official API has been connected. The normal database may therefore remain empty. Permitted official source requests previously returned 403/503; the expanded research network draft is saved but was not active. Permission to research is already authorized; inaccessible sources cannot establish facts.

Actual HTTPS origins/provider access, persistent hosted database/backup operations, external SMTP delivery and hosted auth/core acceptance remain unverified. Process-local rate limiting is not deployment-wide protection. The privacy page accurately states there is no automatic account deletion/retention purge. Local Linux Chromium/automated accessibility results do not certify all browsers/devices or production capacity.

Use [WEBSITE.md](WEBSITE.md) for local setup and [DEPLOYMENT.md](DEPLOYMENT.md) for the remaining release gates. The public presentation and seed-free normal local workflow are implemented; the complete public launch is **not yet verified**.
