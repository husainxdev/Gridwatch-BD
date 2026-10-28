# Sections 7–8: user dashboard and community evidence

This phase reuses authentication, saved areas, source review and personal reporting from Sections 1–6. The dashboard uses PostgreSQL-backed APIs; no official feed, sensor connection, verified Sylhet dataset, feeder registry or complaint contact has been invented.

## Private APIs and preferences

`GET /api/saved-areas` retains its location-shaped `items` and now adds `label`, `is_default` and `available`. Only the current user's records are returned. A location is available for reporting/default selection when its verification status is verified. Root/demo fixtures remain separate from operational locations.

`POST /api/saved-areas/{location_id}` saves a verified location, returning `already_saved` for a duplicate. It does not change the default. `PUT /api/saved-areas/{location_id}` replaces the current user's short label and default preference:

```json
{"label":"বাসা","is_default":true}
```

Labels are trimmed, at most 60 characters, and optional. Extra ownership fields are rejected. PUT on another user's save returns 404. All save/default/remove mutations take a PostgreSQL user-row lock; a partial unique index additionally enforces at most one default per user. Concurrent default changes serialize; the final committed choice wins. DELETE removes only the current user's save. Removing a default leaves no default; it does not silently choose another area or modify reports.

Returning users load their verified default from the backend. Temporary viewing remains in memory, scoped to the authenticated user, across navigation. A full reload uses the backend default; viewing a different area never changes it. Default and labels therefore persist across devices; temporary viewing does not. Unavailable defaults prompt explicit selection. Removal of a viewed saved area, a missing location, or lost verification produces a clear fallback without choosing an unrelated area. An unavailable default can be cleared or removed. Logout/failed session refresh clears all private frontend cache and viewing memory.

## Dashboard snapshot

`GET /api/dashboard?location_id=UUID&page=1` requires an active authenticated session. Location is explicit; an omitted parameter returns validation error. The service checks auth before opening a read-only-use REPEATABLE READ snapshot, so its bounded query set sees consistent data. There is no N+1 notice/ancestor fetch per card. API responses use `Cache-Control: private, no-store` (also applied to other API routes).

The response includes:

- `area`, availability and ordered administrative `breadcrumb`.
- `schedules`: ten windows per page, deterministic start/UUID order, total count, calendar bounds, each joined to its notice's declared issuing office, original URL and review/publication/update metadata.
- `community`: the same backend rules as `/api/reports/summary`, plus distinct reporter count, window, latest observation and retrieval time.
- `personal`: only this user's selected-area latest applicable observation, unresolved episode (or most recent closed episode), five recent activities and five recent personal episodes.
- `retrieved_at` and `restoration_estimate: null` (no trustworthy estimate configured).

The schedule window covers today and the following seven calendar days in Asia/Dhaka. Interval overlap includes windows crossing midnight; windows ending exactly at today's midnight are excluded. Cancellation and revision statuses remain explicit. Draft/unverified/archived/withdrawn notices and unpublished/demo schedules stay excluded. Overlaps are shown independently; they do not become multiple verified outages. Historical records outside this bounded calendar range remain available through existing APIs; the dashboard does not claim they do not exist.

Exact selected-location matches retain their explicit scope. New/revised schedule coverage now snapshots ancestor IDs alongside names/kinds. A parent dashboard can display a snapshot-matched named descendant with a clear **partial coverage** warning; it never implies that every household is affected. Snapshot matching does not use current hierarchy changes to rewrite historical coverage. Older coverage records without ancestry metadata still support exact matching; historical ancestry is not fabricated/backfilled. The existing public schedule-list location filter continues to mean an exact explicitly named location. There is no automatic propagation of parent announcements to every descendant, and no inferred feeder coverage.

Schedule labels distinguish upcoming, within announced window, announced window ended, cancelled and revised. A clock tick does not create a report, close an episode or change power status. The UI says no published schedule was found in the displayed range, without promising availability. Estimated restoration, planned window end and personal observed restoration remain distinct.

## Community and personal evidence

`COMMUNITY_WINDOW_MINUTES` defaults to 60, validated between 5 and 1440. SQL ranks eligible observations by reporter, observed time, submitted time and UUID, then aggregates only rank 1. Reports must be accepted, non-demo and inside the past observation window; future observations are not counted yet. This downloads at most three aggregate rows rather than a paginated/raw population. Repeated updates count as one person; restoration replaces that person's previous off count. Counts, `unique_reporters`, timestamps and `evidence_label` contain no reporter identities or notes.

Evidence descriptions are no_recent_reports, interruptions_reported, mixed, or restoration_reports. Area status remains unknown; no count is a universal power claim. Source observation age and retrieval time are separate. Rejected, pending, expired and demo evidence does not enter current counts. Personal open episodes persist even when community observations age out.

The three report actions use the Section 6 submission endpoint and unchanged ownership/duplicate rules. A successful action refreshes the current snapshot. A failed/uncertain request retains its exact payload/key for retry while mounted. Changing areas cancels obsolete reads and prevents a late result or action feedback from replacing the newly selected area's data. “আমার এখনো আসেনি” preserves an open personal episode. Without an episode, it records a current observation with unknown start. Other people's restoration never closes it. No complaint contact appears because a verified contact/coverage source is not available.

Personal elapsed time uses recorded `started_at`, with `ended_at` when closed. It clamps negative elapsed values, survives reload, and stops advancing after recorded restoration. Unknown starts have no invented duration. Closed/incomplete history keeps unknown endpoints explicit. The dashboard shows recent activity, not an unbounded download of all private history.

## Polling, freshness and failures

`VITE_POLL_INTERVAL_MS` defaults to 30000; the frontend clamps it to 5000–300000 ms. Changing Vite variables requires restarting the dev server/rebuilding. `usePolling` shares entries by user and full query path (including location/page); there is one request/timer per active key and no overlapping refresh. Hidden/offline pages cancel work and pause timers. Visibility/connection return triggers refresh. Consecutive failures use exponential backoff, capped at five minutes. Manual refresh uses the same in-flight request rather than starting duplicates. Unused subscriptions stop polling and obsolete requests are aborted. The bounded in-memory cache holds no authentication tokens and is cleared at logout/session failure.

Previously successful data is retained for the same key after a transient failure and explicitly marked outdated. Failed requests never become false zero-count/no-record states. Reporting is disabled while location data is unavailable/outdated due to an error. A snapshot older than two polling intervals is also marked stale. Authentication expiry uses the existing single-flight refresh flow; a failed refresh clears private state. Periodic polling is described honestly, without claiming instantaneous/official monitoring.

`EvidenceCard` separates source/observation time, GridWatch record or submission update, and last successful retrieval. An authority's independent source-update timestamp is unknown unless supplied by a trusted source; it is not substituted with GridWatch's row-update time. Admin source review does not imply government endorsement. All display times use Asia/Dhaka. Motion respects reduced-motion preferences; native labelled controls, focus outlines and text states work without relying only on color.

## Migration and local checks

Migration **0004** adds saved-area labels/defaults, a partial unique default index, the report-area aggregation index and a GIN coverage index. Existing saves get empty labels and no default; no arbitrary default is assigned. Back up populated deployments before migration. Setup continues to seed only isolated fictional demo areas.

Linux/cloud:

```bash
cd backend
.venv/bin/alembic upgrade head
.venv/bin/alembic check
.venv/bin/uvicorn app.main:app --reload --port 8000
```

From a second terminal at repository root: `npm run dev --prefix frontend`.

Windows Command Prompt, from your existing project folder (keep your existing `.env` secrets and custom database port):

```bat
cd backend
.venv\Scripts\python.exe -m alembic upgrade head
.venv\Scripts\python.exe -m uvicorn app.main:app --reload --port 8000
```

Second Windows terminal at the project root: `npm.cmd run dev --prefix frontend`. Keep Docker Desktop/database and both application terminals running. Do not overwrite `.env` or discard your local Compose port change when updating Git.

Validation commands from repository root:

```bash
python3 scripts/test.py
backend/.venv/bin/ruff check backend
backend/.venv/bin/ruff format --check backend
npm run lint --prefix frontend
npm run format:check --prefix frontend
npm run build --prefix frontend
CHROMIUM_EXECUTABLE=/usr/bin/chromium python3 scripts/browser-test.py
```

The database runner uses uniquely named disposable databases. It checks empty upgrades, downgrade/upgrade, metadata agreement and a populated 0003→0004 saved-area upgrade without losing the row. The browser runner uses separate test ports and fictional accounts/locations; no real database is reset. Backend checks cover concurrent defaults and ownership, mixed/latest evidence, personal restoration independence, stale/demo/rejected exclusion, midnight/cancellation/revision/partial coverage and bounded query count. Browser checks cover first-time/default selection, mobile/keyboard/reduced-motion, persistent timers, two-account still-off/restoration, rapid switching, stale failures, poll deduplication/backoff/visibility/offline behavior, unavailable defaults and auth failure clearing.

Manual review: login → select/save area → label/set default → reload or sign in on another device → inspect source/coverage/times → report off → have another account report restoration → original user reports still off → refresh and verify unresolved episode → original user reports restoration. Disconnect networking and verify retained cards are clearly stale; reconnect and refresh. Remove/unverify the default and confirm a deliberate selection prompt. Repeat on mobile.

No hosted deployment, real outage verification, cross-tab refresh redesign, new complaint directory or additional infrastructure is part of this phase. Frontend automated validation uses Chromium; Windows/macOS native browsers and screen-reader behavior have not been independently tested here.

Validation recorded: **37 backend tests passed**, including populated migration preservation and bounded dashboard query count; **8 Chromium journeys passed**, including 1440px/390px layouts, two-account personal status, controlled polling timers, stale network recovery and unavailable defaults. TypeScript lint, Prettier, Vite production build, Ruff lint/format and Git whitespace checks passed. One upstream Starlette/httpx deprecation warning remains. Targeted mobile/desktop dashboard captures were inspected locally; no real user credentials or mail were captured.
