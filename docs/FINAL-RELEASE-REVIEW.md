# Current release review — 6 November 2026

This is a local release candidate, not evidence of a public deployment. The user requested a usable public website and broad final checks. Work preserves Next.js/React/TypeScript/Tailwind/DaisyUI and the FastAPI/PostgreSQL application. No user database was reset and no fictional electricity observations were published.

## Fixed

- The area explorer now searches both source branches by default while preserving current/historical identity, review and reporting boundaries. Typing searches without an extra submit or source switch. Multiword ancestor context, case and Bengali-digit normalization, exact-name ranking, deterministic pagination and type filters are supported.
- Homepage area search displays actual historical neighborhood matches with ancestor context and navigation into the full directory. Historical entries still cannot become saved/report targets.
- Replaced the directory's technical form with a responsive hero/search, quick searches, district browsing, legible cards, inline source disclosure, breadcrumbs and keyboard access. Area discovery is a primary mobile navigation action.
- API 404/422 is shown as a service-version problem with retry and retained search, not a zero-result success. Normal startup now checks the real search directly and through Next's proxy before opening the site.
- Fresh bulk imports run PostgreSQL ANALYZE so hierarchy search does not wait for automatic statistics. The old first-import path caused very slow queries in an isolated integration transaction; the corrected focused suite passed in 11.55 seconds.
- Loaded results are keyed to the complete request, preventing previous-page/search cards from appearing under a newly changed URL while the next effect starts.
- Updated the hosting dashboard guide to the actual normal deployment: schema 0007, demo flags disabled, reviewed source import, persistent PostgreSQL, actual HTTPS origins, secure same-origin cookies and external mail acceptance. Earlier demo instructions were incompatible with the normal production guards.

## Local evidence

Tests use disposable PostgreSQL databases and generated test accounts. Production browser tests run the real backend and a production Next build. Controlled interception is limited to reproducing unavailable/obsolete requests, not substitutes for core API flows. Anonymous screenshots contain no credentials or private observations.

Final command results are recorded below after validation. Earlier failed runs informed the fixes and are not counted as passing evidence.

## Launch prerequisites still external

- Actual Vercel/Render projects, HTTPS origins, authorized provider access and persistent hosted PostgreSQL.
- Production secrets configured through the provider; exact frontend CORS/origin, Secure cookies, trusted proxy addresses and matching immutable source SHA.
- Authorized SMTP sender and verified delivery to an owner-controlled recipient; local Mailpit does not prove external delivery.
- Controlled migration/import, private backup restoration proof, hosted signup/session/reset/report/activity/history acceptance and restart persistence.

Nine portal identities still require administrative review. The supplied census is a 2022 extraction, not a verified current ward/feeder crosswalk; per-page reconciliation remains incomplete and village coverage is not complete for the other three districts. No live official outage feed or independently sourced new outage notice was invented. Search supports provided labels and aliases, not arbitrary missing translations or every misspelling. No public uptime/capacity or universal accessibility certification is claimed.

## Checks completed on this candidate

| Command | Result |
| --- | --- |
| `backend/.venv/bin/python scripts/test.py` | 88 passed, 1 upstream Starlette/httpx deprecation warning; fresh/upgrade/downgrade checks and Alembic drift check passed |
| `backend/.venv/bin/python scripts/test.py tests/test_supplied_directory.py tests/test_website.py` | 18 passed, same upstream warning |
| `npm run lint --prefix frontend` | Passed: Next route type generation and strict TypeScript |
| `npm run format:check --prefix frontend` | Passed |
| `npm run build --prefix frontend` | Passed: normal production build |
| `npm run check:release --prefix frontend` | 13 configuration cases passed; no provider contacted |
| `backend/.venv/bin/ruff check backend scripts` | Passed |
| `backend/.venv/bin/ruff format --check backend scripts` | 64 files passed |
| `backend/.venv/bin/python scripts/validate-release-config.py` | Passed local manifest consistency |
| `npm audit --omit=dev --prefix frontend` | 0 reported production vulnerabilities at check time; not a universal security audit |
| Configured-secret scan | 208 tracked source/build files checked; no configured JWT/DB/SMTP matches; not universal secret detection |
| Normal launcher | Schema/import retained, search verified directly and via Next proxy; no account/reset/fixture creation |

Five sequential anonymous local requests through Next's development proxy, 6,193 source records, concurrency 1: 62.9–80.2 ms, median 69.7 ms. Queries were Bengali neighborhood, English ancestor+neighborhood, Bengali upazila, broad Sylhet and Bengali ward digits. This small local observation does not establish hosted capacity. PostgreSQL 17, Chromium and the current managed Linux workspace were used.

Representative anonymous views were inspected at 390 and 1440 pixels: [districts/mobile](screenshots/explorer-390.png), [districts/desktop](screenshots/explorer-1440.png), [search/mobile](screenshots/explorer-search-390.png), [search/desktop](screenshots/explorer-search-1440.png). Automated directory/layout checks also cover 360 and 768 pixels. Physical Windows/browser extensions, mobile on-screen keyboard hardware and full screen-reader certification were not tested here.

## Owner acceptance after pulling

1. Stop earlier API/frontend terminals; run `START-WEBSITE.cmd` and leave its terminal open.
2. Open `/areas`, type `আম্বরখানা`, `Airport Ambarkhana` and `বালাগঞ্জ` without clicking Search; inspect names, ancestry and source labels.
3. Browse a district/upazila and return with Back. Filter villages and go to page 2. No old page should remain under new page controls.
4. Open an administratively verified area's electricity information; sign up, save/default the area, reload and log out. Check the account is not still shown as logged in.
5. On the actual HTTPS deployment, repeat the private acceptance checklist, including reset mail and persistence, before announcing public availability.

A browser publication journey also navigated with a full document load immediately after clicking Logout, canceling its queued session request before confirmation on one full run. The journey now asserts the actual logged-out navigation state before opening registration. No auth checks were removed and no timeout was increased to hide the failure. Server revocation and cross-account boundaries are independently exercised by backend and multi-tab/browser tests.

## Final browser acceptance

`CHROMIUM_EXECUTABLE=/usr/bin/chromium backend/.venv/bin/python scripts/browser-test.py` on the final candidate: **34 passed, 3 skipped, 2.1 minutes**. The skipped cases require the separate historical private demo server; they are not normal-site auth/reset/publication/history checks. The normal suite exercised signup/saved areas/logout at desktop/mobile, real notice publication, independent reports, activity/history, reset single use, revoked sessions, two-tab coordination, stale/error handling, source-directory pagination and keyboard/axe checks at 360/390/768/1440 widths.

The form-scroll fix passed all four widths; final production browser console checks reported no assertion failures. The paging test now waits for the actual page-2 API response and asserts its exact returned names, instead of sampling the old DOM immediately after the URL changes. The production build and formatting were repeated after the final CSS/test corrections. No external SMTP, hosted URL or physical-device result is inferred from these tests.
