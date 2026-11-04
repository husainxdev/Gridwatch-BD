# Area search repaired against real data — 2026-11-04

The owner reported that areas could not be found and the interface did not support useful work. Inspection confirmed a real prerequisite failure: the normal local database had zero administrative locations. Earlier presentation-only work left search empty. This change supplies a bounded, source-reviewed real directory and fixes the associated navigation/search behavior. It does not invent outage evidence.

## Defects and fixes

| Finding | Cause and repair | Evidence |
| --- | --- | --- |
| Normal area search always empty | No administrative records were installed. Three original government pages now support 45 records: Sylhet division, district, city corporation and 42 general wards. | Actual normal startup imported 45; source URLs/date/excerpts/hash in the manifest; real API/browser selection |
| An existing installation could stay empty or lose human edits | Earlier startup had no verified directory import. First-start import now fills an empty directory only; `--import-catalog` explicitly merges existing directories without overwriting names, source dates, review state or versions. | PostgreSQL preservation, identity reuse, conflict rollback and concurrent-start tests |
| Search failed with extra whitespace or treated `%`/`_` as broad patterns | Exact substring matching of an untrimmed query; frontend allowed 200 characters but API allowed 100. Normalize whitespace/Unicode, match all words, escape literal wildcards, rank exact names/aliases, cap input at 100. | Bengali/English/padded ward-number/UUID searches, bounds, deterministic pages and literal-wildcard tests |
| Picking a ward on Home then logging in lost the area | Dashboard never read `location_id` from its URL. It now consumes and synchronizes the explicit area through auth, reload and URL changes. | New real signup → selected ward → save → reload journey; development browser check additionally exercises switching to Ward 2 then browser Back to Ward 1 |
| New URL synchronization cleared unavailable-area warnings | An internal URL update was mistaken for an external selection, clearing fallback copy; saved-default state also needed consistent messaging. Track the internally applied request and preserve the specific unavailable-default message. | Existing strict unavailable-default regression failed during this change, then passed without weakening the assertion |
| Finding a ward required navigating every administrative level | Add real city shortcuts, ancestor context, all 42 ward buttons in a bounded scrollable grid, keyboard search results, separate lookup/selection errors, loading/empty/retry states and source/date detail. | Actual grid at 360/390/768/1440, keyboard selection, axe/overflow and direct source-link assertions |
| Large landing cards delayed the main task | Replace the tall marketing hero with a compact task heading, put area selection first, and move secondary workflow links after the evidence. | Anonymous normal-site screenshots, manually inspected |

## What the directory proves

Original sources and caveats are recorded in [DATA_SOURCES.md](DATA_SOURCES.md) and [`data/sylhet-city-locations.v1.json`](../data/sylhet-city-locations.v1.json). Administrative verification occurred at 2026-11-04 10:54:45 UTC. The source-reviewed 42 general wards exclude the 14 reserved-seat groupings. Historical 27-ward prose in the city overview was not used as current coverage; a separate recent government assignment table corroborates 1–42.

No officer phone/email was imported. Search aliases are curated translations/spellings, not official codes. Internal UUIDs are deterministic application IDs. No neighborhood-to-ward boundary, police unit, electricity office, feeder mapping, notice, schedule, report or outage episode is created by this import.

The importer makes no startup network call. It uses one transaction, hierarchy/advisory locks and existing uniqueness rules. Existing matching administrative identities can be reused, including names without their type suffix; they are never automatically renamed or re-verified. Conflicts roll back all attempted inserts. Automatic startup does not refill individual deleted/deactivated records in a nonempty directory; an explicit operator merge is required. Original Admin audit/permission behavior is preserved; initial catalog provenance is the versioned manifest plus each location's source/date, not an invented human reviewer account.

## Actual checks

| Command / check | Result |
| --- | --- |
| `backend/.venv/bin/python scripts/test.py tests/test_location_catalog.py` (first focused pass) | Six passed before the additional short-name preservation case |
| `backend/.venv/bin/python scripts/test.py` (final) | **78 passed**, one existing Starlette/httpx deprecation warning; fresh/populated migration checks and no schema drift, head remains `0006` |
| `CHROMIUM_EXECUTABLE=/usr/bin/chromium backend/.venv/bin/python scripts/browser-test.py` (final) | **30 passed**, **3 skipped**, about 2.6 minutes. The skipped cases are historical dedicated-demo server journeys. Real normal auth, permissions, publication, reporting, conflicts/history, session/reset, catalog and UI checks ran. |
| `GRIDWATCH_BROWSER_MODE=development CHROMIUM_EXECUTABLE=/usr/bin/chromium backend/.venv/bin/python scripts/browser-test.py cancellation.spec.ts location-catalog.spec.ts` | **Three passed** in 14.5 seconds; includes the added Ward 2 → browser Back → Ward 1 assertion, real catalog/account flow, grid accessibility and pending cancellation in Next development mode |
| `npm run lint --prefix frontend` | Passed: Next route generation and strict TypeScript/unused checks |
| `npm run format:check --prefix frontend` | Passed |
| `npm run build --prefix frontend` | Passed: optimized Next build |
| `npm run check:release --prefix frontend` | 13 configuration cases passed; no provider contacted |
| `backend/.venv/bin/ruff check backend scripts`, `... ruff format --check backend scripts`, `git diff --check` | Passed |
| `scripts/start-website.py --check-only` | Empty normal directory received 45 reviewed administrative records; no electricity records/accounts created |
| `scripts/start-website.py --check-only --import-catalog` | Repeated merge preserved the existing records |
| Targeted configured-secret/static-output scan | 278 files checked; no configured local DB/JWT/SMTP secret or generated private password matched. Bounded scan, not universal secret detection. |
| Actual anonymous normal UI inspection | Direct city/ward selection, original source link, unknown power status, no page errors/overflow; 390/1440 screenshots |
| Accessibility | New 42-ward grid and original core pages checked at 360/390/768/1440 with axe A/AA rules and keyboard interaction. No full device/screen-reader certification claimed. |

Intermediate browser runs genuinely exposed the lost-area bug and then the unavailable-default regression; both were repaired. Existing permission/error/a11y expectations were retained. The search label assertions now match the simpler visible Bengali label, rather than an obsolete internal-ID-oriented label. All browser test identities/observations/mail remain in disposable databases and controlled mail sinks. The normal local DB received only the authorized real administrative directory; no fake electricity report or test account was published.

Screenshots: [mobile picker](screenshots/area-finder-390.png), [desktop picker](screenshots/area-finder-1440.png), [mobile ward](screenshots/ward-overview-390.png), [desktop ward](screenshots/ward-overview-1440.png). No signed-in identity, secret, token or invented outage evidence is present.

## Owner update and manual acceptance

Stop earlier API/frontend terminals with Ctrl+C. From CMD or PowerShell:

```text
git -C "C:\Users\USER\Gridwatch-BD" pull --ff-only
C:\Users\USER\Gridwatch-BD\START-WEBSITE.cmd --import-catalog
```

Open **http://localhost:5173/**. Click **সিলেট সিটি কর্পোরেশন**, choose a ward, or search **Ward 1 / ওয়ার্ড ১**. Check the original source/date. Register/log in, confirm that the ward survives, save it, reload, switch area and use browser Back. A source-reviewed administrative location does not mean power availability is known.

## Remaining boundaries

Neighborhood/street names (including আম্বরখানা) are not assigned to wards without original boundary evidence. Outside this small city directory, new areas still require review. There is still no verified official live outage feed, provider/feeder coverage or public HTTPS deployment. Zero observations remains unknown power status; there are no fabricated schedules to make the page look busy. External SMTP delivery, hosted persistence/backups and live acceptance remain required before public release. No production-readiness claim is made from local test results.
