# Supplied Sylhet directory: implementation and validation

The owner supplied `GridWatch_BD_Sylhet_Locations.sqlite`. It is geographic/source reference data, not the full operational application database. The existing FastAPI/PostgreSQL backend and Next.js frontend remain in place. The original source file is preserved, read only and checksum-bound; its embedded guide/SQL suggestions are never executed as instructions.

## Contents and review boundary

| Source data | Preserved count | Handling |
| --- | ---: | --- |
| Portal administrative records | 428 | 419 matched original source names/parents or the existing reviewed city catalog; nine remain unverified |
| Census 2022 place records | 5,765 | Separate historical branch; original kinds, parents, codes and claimed PDF pages retained; no current Location/report mapping |
| Source links | 19 | Original titles, URLs and scope retained; a link alone is not a verification claim |
| Review queue | 4 | Preserved; no disputed excluded entry silently restored |
| Union-roster checks | 41 | Preserved as provenance |
| Utility/locality examples | 32 | Read-only references only, never active feeder coverage |
| Guide notes | 9 | Inert source data; no supplied SQL/view/command executed |

The 428 portal rows contain 4 districts, 41 upazilas, 339 unions, the division/city corporation and 42 wards. The census extraction covers **Sylhet district**, not all villages of the other three districts. Census thanas, municipal ward segments and mouza segments remain their original types, without being forced into the active administrative hierarchy. Search aliases such as আম্বরখানা are curated spelling aids only.

The BBS URL returned an 821-page PDF; supplied page 164 rendered blank during this review. Per-row and page-number reconciliation is **unverified**. The application explicitly labels the historical branch and claimed pages; no current boundary crosswalk is approved. [Full source evidence and hashes](DATA_SOURCES.md).

## Database and import

Migration `0007_source_directory.py` adds `directory_datasets` and `directory_places`, and permits a missing `locations.name_en` instead of inventing 379 English labels. Case/whitespace uniqueness remains enforced for supplied English labels; Bangla/parent/type uniqueness remains unchanged.

The source reader checks file size/integrity, allowlisted base tables, foreign keys, parent graphs, names, snapshot metadata and safe HTTPS source destinations. Views, triggers, extensions and guide text are not executed. Before application import, the file hash must match the separately reviewed manifest. Runtime import makes no external fetch.

One transaction and existing hierarchy locks cover related changes. Existing 45 reviewed pilot IDs, source dates, Admin versions/names/verification states and all user/power records are preserved. First import creates 383 additional current location rows, plus all 6,193 separate source records; repeating the same dataset is a no-op. Historical rows have a database constraint forbidding a current `location_id`. Unverified portal rows cannot be used for reporting until the existing Admin workflow resolves them.

Downgrade refuses to erase imported directory data or manufacture missing English names. Use reviewed forward migrations; do not delete a normal database/volume to force a downgrade.

## Run locally

Stop earlier API/frontend terminals, then from CMD or PowerShell:

```text
git -C "C:\Users\USER\Gridwatch-BD" pull --ff-only
C:\Users\USER\Gridwatch-BD\START-WEBSITE.cmd
```

The launcher preserves existing configuration/custom ports, creates a private custom-format PostgreSQL backup before an older populated local schema upgrade, migrates under the controlled helper, and performs the one-time import. Backup failure stops the upgrade. Receipt files state that restoration has not been performed for that individual backup; no restoration claim is invented. The app's isolated backup/restore regression checks remain separate.

Open **http://localhost:5173/areas** or **এলাকার পূর্ণ তালিকা**. Use **প্রশাসনিক তালিকা** for `বালাগঞ্জ`, or **গ্রাম / মহল্লা · ২০২২** for `Ambarkhana` / `আম্বরখানা`. Source/parent/year information is visible. Only reportable verified current locations link to active power information; historical results never do.

For controlled operator use after migration, with an explicitly selected database:

```bash
backend/.venv/bin/python scripts/import-supplied-directory.py --expected-database ACTUAL_NAME
```

The CLI never logs credentials or resets data. Hosted production remains a separate configured deployment, not this local launcher.

## Public API

- `GET /api/directory/summary`: counts, source links and review/utility references; no user/session data.
- `GET /api/directory?branch=portal|census2022&search=...&page=1&page_size=20`: stable bounded listing; validated limits (1–50), type filtering, literal-wildcard search, ancestor context and actual current reportability.
- `parent_id=UUID` lists children only within the same snapshot. `roots_only=true` lists source roots. Census and portal roots are separate.
- `GET /api/directory/{UUID}`: original record/source and breadcrumb. Census PDF page is explicitly claimed metadata, not a row-level verification claim.
- Existing `/api/locations` serves only active administrative records; there is no current-location API containing merged historical wards/thanas.

## Validation evidence

The complete backend/browser/static results are recorded at handoff below. All destructive tests target UUID-named isolated databases; no real recipient received email and no fake power report/account was created in the normal database. The normal database received the authorized directory only, after a real private backup.

Known limits: nine unresolved portal records, unverified census page/row matching, missing village rows for three districts, no current neighborhood/feeder crosswalk, no official live outage API and no verified public deployment. The app is not declared production-ready from local tests.

## Executed checks and actual results

| Check | Actual result |
| --- | --- |
| `backend/.venv/bin/python scripts/test.py` | **86 passed**, one upstream Starlette/httpx deprecation warning; empty/populated migration round trips and Alembic no-drift check passed |
| Final focused `... scripts/test.py tests/test_supplied_directory.py` | **8 passed** after the approved-file checksum was moved before SQLite schema parsing; covers immutable source counts, malformed input, idempotency, existing IDs/reviews, historical isolation, paging/limits, null-label uniqueness, downgrade refusal and saved-area protection |
| `CHROMIUM_EXECUTABLE=/usr/bin/chromium backend/.venv/bin/python scripts/browser-test.py` | **31 passed, 3 skipped** in about 3.2 minutes; skipped cases are historical dedicated-demo server cases, not the new normal directory flow |
| Final production focus: `... scripts/browser-test.py source-directory.spec.ts public-home.spec.ts` | **3 passed**; current/census browsing, child navigation, historical report-link exclusion, Bengali search discovery, and public home/private navigation regressions |
| Development mode: `GRIDWATCH_BROWSER_MODE=development ... scripts/browser-test.py cancellation.spec.ts source-directory.spec.ts` | **2 passed**; no pending-request rejection or page exception |
| Expanded development directory focus after contrast fix | **1 passed**, checking both portal and census results with axe A/AA rules at 360/390/768/1440px plus child navigation |
| `npm run lint --prefix frontend` | Passed: Next route type generation and strict TypeScript/unused checks |
| `npm run format:check --prefix frontend` | Passed after fixing formatting in the previously committed location-catalog browser test |
| `npm run build --prefix frontend` | Passed, optimized Next build includes `/areas` |
| `npm run check:release --prefix frontend` | 13 cases passed; no provider contacted |
| Ruff check/format and `git diff --check` | Passed |
| Actual normal local upgrade/start | Private PostgreSQL backup created, schema `0006 → 0007` applied, source directory imported into PostgreSQL, existing 45 pilot IDs preserved |
| Anonymous normal UI captures | Portal and census states at 390/1440px; no page error or horizontal overflow, no signed-in account/credentials |
| Targeted configured-secret/static scan | 297 source/static files checked; no configured DB/JWT/SMTP secret or generated private password matched. This is not universal secret detection. |

Manual screenshot inspection found that the old generic inline-link rule made primary action text dark on a dark button. The rule now excludes button links; the expanded current-and-historical accessibility checks verify the fix without suppressing contrast rules. An initial backend assertion assumed 380 missing English labels; inspecting the actual source showed 379 because Silam has a supplied English label. The assertion was corrected to that source fact, without manufacturing translations.

Actual captures: [portal mobile](screenshots/directory-portal-390.png), [portal desktop](screenshots/directory-portal-1440.png), [census mobile](screenshots/directory-census-390.png), [census desktop](screenshots/directory-census-1440.png). Browser/API tests used isolated PostgreSQL and controlled mail adapters. Physical Windows devices, screen-reader certification and hosted HTTPS acceptance remain unverified.
