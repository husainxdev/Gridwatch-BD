# Sections 9–10: administration, activities and personal history

This phase extends the existing application and PostgreSQL records. It does not implement deployment, reminders, official data ingestion. Operational data is not seeded with invented Sylhet records.

## Admin workspace

`/admin?tab=overview|notices|schedules|reports|events|areas|offices|mappings|publishers|audit` is protected by the existing Admin route and backend dependency. Existing notice/schedule/location/event forms and mutation APIs are reused. Browser search is debounced, obsolete list requests are cancelled, and filters, sorting and pagination are URL state. Back/forward restores that state. Empty last pages move to the last available page after a successful mutation. The schedule notice selector has its own paginated search; it is not restricted to the first hundred notices.

Overview counts exclude demonstration notices/schedules/reports:

| Key | Exact meaning |
| --- | --- |
| `draft_notices` | All draft notices, whether already source-reviewed or not; still awaiting publication |
| `upcoming_schedules` | Announced, published schedules starting at or after retrieval time, attached to verified, published, non-demo notices |
| `pending_reports` | Individual reports whose moderation state is pending; not an outage count |
| `unrestored_events` | Existing evidence-backed event records without a recorded restoration; not a count of candidates or households |

There is no separate candidate-event lifecycle in the existing model. `candidate_events_supported=false` is explicit. Reviewed report associations can be added/removed from existing event records. Closing an event never closes personal episodes. Office and feeder-mapping pages now have persisted, versioned create/edit/review/activate/deactivate/delete workflows. Their original sources and explicit coverage descriptions are required. A separate publisher directory links raw notice publisher strings to notices; those strings are not automatically considered office identities. There are no seeded real offices or feeders.


## Admin APIs

All endpoints below require an active Admin session.

- `GET /api/admin/overview` — counts above and retrieval time.
- `GET /api/admin/list/{entity}` — `notices`, `schedules`, `reports`, `locations`, `events`, `audit`. Returns `items,total,page,page_size`. Parameterized search, allowlisted sort expressions and a UUID tie-breaker. Page starts at 1; size 1–100 (UI uses 10). No client-side imitation of pagination.
- Shared filters: `search`, `status`, `start`, `end`, `sort=newest|oldest|name|time`. Aware date bounds are `[start,end)` on schedule start, report observation, event start, or creation time for other entities. Invalid sort/status/date bounds return 422.
- `location_id`: exact explicit schedule coverage, notices naming that coverage, report/event location, or immediate parent for locations. `office` means exact notice publisher, also applicable to schedules. `category` applies to schedules and their notices. `kind` applies to locations/reports. Unsupported entity/filter combinations return 422.
- Status: notice lifecycle; schedule lifecycle or cancelled/superseded (published additionally requires announced status and a currently visible notice); report moderation; location verified/unverified; event open/completed.
- Search: relevant title/category/kind/name/action/evidence or exact UUID; locations include English/Bangla/aliases; schedule search also searches its notice title; audit search includes entity UUID.
- `GET /api/admin/reports/{id}/context` — related personal episode and at most 20 time/exact-area matching announcements with source links. This is a contextual match, not proof of causation.
- `GET /api/admin/offices?search=&page=&page_size=` — grouped notice publishers/counts and explicit distinction from the reviewed registry.
- `GET /api/admin/list/audit?search={record UUID}` — paginated revisions across entities. The older `/api/admin/evidence/{entity}/{id}/revisions` route is retained, now bounded to 100 with `page`/`page_size`.
- `POST /api/admin/locations/{id}/deactivate` — `{version,reason}` suspends verification, keeps source evidence and references, and supersedes schedules explicitly naming the location. Existing descendants and historical personal records remain intact. They are not reclassified as electrical coverage. Reverification is a separate reviewed action.

Existing mutation routes now use version checks for location edits/verification/deletion, report review and event restoration as well as notices/schedules. A new record starts at version 1. Mutations require the currently returned version; deletion uses `?version=`. For backward compatibility omitted versions on older body schemas mean 1; this can only succeed against an unchanged initial version, never overwrite a later edit. Concurrent updates serialize using row/advisory locks and reject the stale writer with 409. Location create always sets version 1 server-side. Activity writes also use version checks.

Cancel, withdraw and archive require a reason of 5–500 characters. Moderation already requires a reason and now checks report version. Original report kind/observation/submission times remain unchanged. Ordinary APIs cannot modify/delete audit rows. Transactional `changes` entries record actor, entity, action, timestamp, before/after fields and reason alongside earlier source snapshots; automatic change snapshots exclude private notes and reporter identity. The existing detailed evidence snapshots remain Admin-only. No auth records, password hashes or tokens enter this trail. Audit storage is not claimed tamper-proof against a database administrator.

Referenced locations cannot be deleted, including activity/episode references. Published evidence cannot be hard-deleted by first revising it back into a draft: its publication audit blocks deletion. Cancel/archive preserve history. No bulk destructive endpoint exists.

## Electricity registry APIs

- `GET/POST /api/admin/registry/offices`; `PUT /api/admin/registry/offices/{id}`. Fields: `name_bn`, `name_en`, original HTTPS `source_url`, current `version` on edit. Names are whitespace/NFKC normalized; English names have a normalized database uniqueness constraint.
- `GET/POST /api/admin/registry/mappings`; `PUT /api/admin/registry/mappings/{id}`. Each record is one explicitly evidenced `feeder_name` / `office_id` / `location_id` claim with a 12–1000-character `coverage_description` and HTTPS source. It does not imply the whole location is served. The normalized name/office/location tuple is unique. Multiple claims can describe one feeder's separately sourced coverage.
- Lists are paginated (1–100), stable-sortable and searchable by name/UUID, with verified/unverified and active filters. Mappings additionally filter by office/location. Names are batch joined; `usable` requires active/reviewed mapping and office plus a verified administrative location.
- `POST /api/admin/registry/{offices|mappings}/{id}/{verify|activate|deactivate}` takes `{version,reason}`. Review is a recorded Admin source review, not government endorsement. Edit always resets review; activation does not verify. Office identity edits/suspension and location edits/suspension invalidate affected mappings and increment their versions.
- `DELETE /api/admin/registry/{entity}/{id}?version=N` is limited to never-reviewed, unreferenced drafts. Previously reviewed claims must be deactivated. Office and location foreign keys preserve referenced evidence.
- All routes are Admin-only; all changes join the same immutable-through-API audit trail. No public endpoint can submit verification/actor fields. The registry has no official API connection, no manufactured official codes, and no seeded real records.
- Registry claims are intentionally not silently connected to older notice publisher strings or schedule feeder IDs. Schedules still require explicitly source-named locations; automatic feeder-to-schedule propagation remains unsupported. This prevents an Admin boundary or loosely matched name from inventing electrical coverage.

## Activity APIs and coverage

All activity endpoints require authentication and derive ownership from the session. Other users' activity IDs return 404 for read/update/delete. Private responses use `Cache-Control: private, no-store`.

- `POST /api/activities/check`: `{location_id,starts_at,ends_at}`.
- `POST /api/activities`: the above plus `title` (1–160 nonblank characters); persists the activity, not a supposedly permanent conflict result.
- `GET /api/activities`: paginated own activities; optional title `search`, `location_id`, `sort=newest|oldest|start`.
- `GET /api/activities/{id}`: owned record plus a **fresh** `check` using current announcement state.
- `PUT /api/activities/{id}`: full body plus current `version`.
- `DELETE /api/activities/{id}?version=N`.

Times must have an offset, end must follow start, and an activity can span at most seven days. UI input/output uses Asia/Dhaka. Invalid/unverified locations return 404/422. The saved list still permits deletion when its location is unavailable; checking cannot claim coverage there.

Only verified/published/non-demo notices and announced/published/non-demo schedules can match. Overlap uses `activity_start < schedule_end AND activity_end > schedule_start`. Boundary-touching windows do not overlap. Each result includes clipped activity bounds, schedule revision, original source, publisher, source publication time (possibly unknown), GridWatch update time and coverage scope. Definite intervals are merged before calculating `affected_minutes`, never summed twice. Cancellation, revision-to-draft and republication affect the next check immediately.

Exact named coverage matches. An explicitly declared **entire administrative area** may apply to a selected descendant only when its ancestor chain has not changed since that schedule was created. Later hierarchy edits are conservatively uncertain. Named descendants seen from a broader selected area, or an ancestor named without a whole-area declaration, are returned separately as `uncertain`; their time is not included in the definite affected total. Older records lacking ancestor snapshots do not gain invented historic descendant coverage. This is interpretation of the announcement, not verification of a household connection or feeder.

At most 500 matching announcements are evaluated per check; a denser result returns 422 asking for a narrower time interval, rather than silently truncating. No matching published interruption is a search result, never an electricity availability guarantee. Reminders/notifications are absent.

## Personal history definitions

`GET /api/history?location_id=UUID&start=aware-time&end=aware-time&status=all|open|completed|incomplete&sort=newest|oldest&page=1&page_size=10`.

One authenticated user and one location per query. The UI treats the chosen final date as inclusive by sending the following Bangladesh midnight as the exclusive API end. Maximum range is 366 days. The calculation reads at most 10,001 episodes, refuses ranges with more than 10,000, and sends only the requested page plus bounded daily aggregates. Counts, duration and returned rows use the same status/range filters inside a REPEATABLE READ snapshot, so concurrent moderation cannot mix old summaries with new rows. Indexed user/location/last-observation access and batched report/review counts avoid per-episode queries.

- Source is accepted, non-demo personal observations. Pending/rejected observations are excluded by the existing moderation rebuild. Future-dated submissions within the configured clock-skew allowance are retained as pending and cannot be accepted before their observation time; they never restore an episode early. Reports and episodes are distinct. Several off/still-off observations share one open episode.
- Consecutive restoration confirmations now stay with the preceding episode and preserve its first reported restoration. The same rule is used by moderation rebuilding. Previously stored episodes are preserved by migration; an Admin review rebuilds the affected reporter/location if legacy duplicate restoration episodes need correction. Migration does not silently rewrite original observations or manufacture a restoration time.
- A lone restoration may produce an incomplete episode with unknown start. A still-off observation without a known start has unknown duration. An open episode never contributes completed duration or an average.
- `recorded_episodes` counts stored episodes whose known interval overlaps the range, with unknown start conservatively bounded by the last observation; `starting_in_range` counts those with an actual known start in `[start,end)`. Unknown bounds cannot establish an exact historical overlap. The UI says this explicitly.
- `completed` has known start/end and is closed. `open` is unresolved. `incomplete` is closed but missing a bound. Negative bounds are rejected by the database constraint; the calculation service also flags contradictory supplied intervals and excludes them.
- `known_minutes` unions completed intervals within **this user's selected location**, clipped to the range. Open/incomplete time is unknown, not zero measured downtime. Overlapping recorded intervals flag review and suppress the average.
- `average_completed_minutes` uses full durations of eligible completed episodes overlapping the selection, not clipped durations. One eligible episode is enough; no eligible records or contradictory/overlapping evidence yields null. The denominator is stated in the UI.
- Daily known minutes split unioned intervals at Asia/Dhaka midnight. Only days with known completed time appear. A readable table is the visualization; no fabricated zero-report trend line is drawn.
- Original source is the user's reports. The page shows accepted observation count and Admin-reviewed observation count. Review may remove/replace reconstructed episodes; episode IDs are not durable external references.

The system does not sum different households, calculate area reliability, or claim SAIDI/SAIFI. Scheduled windows are never converted to actual episodes.

## Setup / migration

No new external credentials are required. The Next.js migration changes frontend dependencies: run `npm ci --prefix frontend` after pulling. The Python lock also includes the reviewed pytest update. Preserve `.env` files and the user's chosen PostgreSQL host port. Docker and the existing database/mail containers must be running.

Windows **PowerShell**, from the project folder (keep backend and frontend in separate open terminals):

```powershell
cd "$env:USERPROFILE\Gridwatch-BD"
docker compose up -d --wait db mail
cd backend
py -m uv sync --frozen --python 3.12
.\.venv\Scripts\python.exe -m alembic upgrade head
.\.venv\Scripts\python.exe -m alembic current
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload --port 8000
```

Expect `0006 (head)`. In a second PowerShell:

```powershell
cd "$env:USERPROFILE\Gridwatch-BD"
npm.cmd ci --prefix frontend
npm.cmd run dev --prefix frontend
```

Open `http://localhost:5173/activities`, `/history` or `/admin`. Running migrations alone does not start either web server. For first-time dependency/config setup use README; an existing setup does not need secrets regenerated.

Linux/cloud migration:

```sh
cd backend
.venv/bin/alembic upgrade head
.venv/bin/alembic current
.venv/bin/alembic check
```

Migration `0005` adds activities, version columns on locations/reports/events and the composite history index. Migration `0006` adds separate electricity offices and explicit source-reviewed feeder claims, with no seed records. Tests apply empty-schema migrations and populated `0003 → 0004 → 0005 → 0006` upgrades, verifying saved preferences/location preservation. Downgrade removes saved activities; it is not an ordinary startup action.

## Verification and manual review

Commands and final validation results are recorded below. Both test runners create uniquely named disposable PostgreSQL databases and clean up only those databases.

```sh
python3 scripts/test.py
CHROMIUM_EXECUTABLE=/usr/bin/chromium python3 scripts/browser-test.py
backend/.venv/bin/ruff check backend
backend/.venv/bin/ruff format --check backend
npm run lint --prefix frontend
npm run format:check --prefix frontend
npm run build --prefix frontend
git diff --check
```

Manual journey:

1. Admin: create/verify/publish a fictional test notice and future schedule only in a test database. Filter by title/ID, change sort/page, then use browser Back/Forward.
2. User: save an activity at that location across the announced window. Inspect source and clipped/union duration.
3. Admin: cancel with a reason or revise/re-publish the schedule. User opens the saved activity again; the fresh result must change.
4. Submit personal off/still-off/back observations. Check one episode, recorded duration and date-range/daily clipping. Another user's reports must not change it.
5. Admin: moderate with a reason and inspect before/after audit. Refresh personal history; original observation timestamps must remain. Closing a broader event must not restore that user's connection.
6. Try a stale version, User access to Admin APIs, another user's activity ID, and deleting a referenced location. Expect 409/403/404 as appropriate; no optimistic success toast.

Known limitations: no externally verified real Sylhet pilot/office/feeder records, no official API, no reminders, no external SMTP/live hosting verification. History is self-reported and may be incomplete. Legacy historical grouping is preserved until reviewed. Registry CRUD/review works, while official ingestion and automatic feeder/schedule linkage remain unavailable. Existing process-local auth rate limiting is unchanged. Sections 11–14 are not completed or certified by this phase.

### Executed validation (cloud, 2026-10-29)

- `python3 scripts/test.py`: **50 passed**, including independent-user history, moderation/rebuild, repeated restoration, source cancellation/revision, exact boundaries, midnight/union/clipping, coverage uncertainty, stale concurrent writes, references and audit snapshots. Empty/populated migration checks and Alembic schema check passed. One upstream Starlette/httpx deprecation warning remains.
- `CHROMIUM_EXECUTABLE=/usr/bin/chromium python3 scripts/browser-test.py`: **13 passed**, against the Next.js production build, including direct routes/client navigation/404 and 1440px/390px Admin publication → saved activity → cancellation → fresh check → personal history → Admin moderation → reopened history, plus existing auth/dashboard journeys and two-tab refresh/account-change/logout checks. URL back-navigation and horizontal overflow assertions passed. Fictional test-only screenshots were visually inspected.
- Ruff check/format, frontend strict TypeScript, Prettier, production Next.js build and `git diff --check` passed.
- Development PostgreSQL `alembic upgrade head`, `alembic current` (`0006 (head)`) and `alembic check` passed; no schema drift.
- The existing dependency lock already includes `tzdata` for Windows via psycopg. No new dependency is needed for `ZoneInfo("Asia/Dhaka")` on the documented Windows install. Windows commands are documented; these checks ran in Linux cloud, not on the user's PC.


Windows verification runners now choose `.venv\Scripts\python.exe` automatically. With Docker running, from the repository root:

```powershell
.\backend\.venv\Scripts\python.exe scripts\test.py
# Install Playwright Chromium first if absent:
cd frontend
npx.cmd playwright install chromium
cd ..
.\backend\.venv\Scripts\python.exe scripts\browser-test.py
```

These runners create disposable test databases. The normal application database is preserved. The automation was executed on Linux; Windows command portability was reviewed, not remotely executed on the user's PC.

See [the implementation review](REVIEW-2026-10-29.md) for additional fixes, the patched pytest dependency, advisory results and remaining architecture/deployment boundaries.
