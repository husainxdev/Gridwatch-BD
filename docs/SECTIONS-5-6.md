# Notices, planned windows and personal observations

Sections 5–6 extend the existing models through migration 0003. No official API, actual feeder registry, Sylhet source verification or file upload service has been added. Existing notice/schedule records become drafts on upgrade: an administrator must explicitly review and publish them. Original content is retained; unknown publication timestamps stay null.

## API contracts

Interactive request schemas are available at backend `/docs`. All mutation routes enforce active authentication and admin or user ownership server-side. Public lists never use saved areas implicitly: omitted location means all publicly eligible records. Page starts at 1; page_size is 1–100; ordered UUID breaks timestamp ties.

| Operation | Endpoint |
| --- | --- |
| Public notices / detail | GET /api/notices, /api/notices/{id} |
| Public schedules / detail | GET /api/schedules, /api/schedules/{id} |
| Admin paginated listings | GET /api/admin/notices, /api/admin/schedules |
| Admin create/update | POST /api/admin/notices or /schedules; PUT /api/admin/{notices,schedules}/{id} |
| Notice review/lifecycle | POST /api/admin/notices/{id}/{verify,publish,withdraw,archive} |
| Schedule lifecycle | POST /api/admin/schedules/{id}/{publish,cancel,archive} |
| Draft deletion | DELETE /api/admin/{notices,schedules}/{id}?version=N |
| Immutable prior snapshots | GET /api/admin/evidence/{notices,schedules,reports}/{id}/revisions |
| Submit / public recent observations | POST /api/reports; GET /api/reports?location_id=UUID |
| Latest-per-reporter evidence | GET /api/reports/summary?location_id=UUID |
| Personal paginated observations / episodes | GET /api/me/reports; GET /api/me/episodes |
| Admin report review | GET /api/admin/reports; POST /api/admin/reports/{id}/moderate |

Notice create/update accepts title, body, publisher (declared issuing office), original HTTPS source_url, nullable published_at, is_demo, version. Source URLs may link directly to a PDF/image; the service never fetches submitted links. GridWatch Admin verification means source review, not that the Admin represents the issuing office. Public notices require verified + published + non-demo. Public schedules also require an eligible notice and their own published/non-demo state. Withdrawn/archived notices hide their linked schedules. Cancellations remain visible with explicit cancelled status until archived.

Updates and lifecycle actions carry the last observed `version`. Row locks and version checks return 409 for stale concurrent edits. Create starts at version 1; verify increments to 2, publish to 3. An edit returns a notice to draft/unverified and supersedes its announced schedules; its original snapshots remain in the audit. Schedule editing returns it to draft and keeps the prior window/coverage in the audit. Republish explicitly after reviewing a revised window. Published records cannot be hard-deleted; use withdrawal/cancellation/archive. Draft deletion also retains an audit snapshot.

Example lifecycle body:

```json
{"version": 2}
```

Schedule create/update accepts notice_id, primary location_id, additional location_ids (up to 100), starts_at, ends_at, category, coverage_scope and version. UTC-offset timestamps are mandatory and end must follow start. Frontend inputs and displays use Bangladesh time. Response window_state is upcoming, within_announced_window or announced_window_ended; none proves actual power status. Overlaps are allowed; creation returns a possible-duplicate warning.

Location matching is exact to explicitly named IDs; no district-to-household or feeder inference. `named_locations` means only the listed areas; `entire_administrative_area` records the authority's explicit scope claim for those same IDs. It does not automatically expand into descendants. Coverage snapshots preserve names/kinds and IDs; changing an administrative hierarchy does not rewrite past coverage. Deleted or unverified mappings are not silently replaced. Verified notice and reporting/coverage locations are required. No verified feeder registry exists: feeder_id submissions return 422 and feeder-filtered reads return no matches. Publisher is declared source-office text, not a separately verified electricity-office identity.

Notice search supports title/UUID, office, location, category, verification status; schedule search supports parent notice title/schedule UUID, location, office, category and announced/cancelled/superseded status. Feeder filtering never invents matches. Schedule date filtering uses `starts_before` and `ends_after`: window.start < starts_before AND window.end > ends_after, so touching boundaries do not overlap. Lists expose explicit pagination. Admin lists currently provide pagination and notice title search; richer Admin listing filters are not implemented.

## Reports and personal state transitions

Example (use a fresh UUID key once per intended observation):

```json
{
  "location_id": "YOUR-VERIFIED-LOCATION-UUID",
  "kind": "power_off",
  "observed_at": "2026-10-28T20:00:00+06:00",
  "idempotency_key": "YOUR-RANDOM-UUID",
  "note": "My connection only"
}
```

Allowed kinds are power_off, power_back, still_off. Ownership always comes from the JWT session; user_id and extra submission fields are rejected. Creation time is controlled by PostgreSQL. Notes are limited to 500 characters, never included in public report lists. No home coordinates are collected. Public summaries expose only aggregated latest observation per reporter in the last hour, exclude pending/rejected/demo observations, and always label area status unknown.

| Observation | Personal episode transition |
| --- | --- |
| First off | Open episode with observed start |
| Further off while open | Reuse same episode, no extra outage count |
| Still off with no open episode | Open episode with unknown start |
| Restoration with open episode | Close only that user's episode |
| Restoration with no prior episode | Closed observation with unknown start/duration |
| Observation older than latest accepted observation | Pending review; current episode unchanged |
| Restoration before linked known start | Reject 422 |

Only known start AND end produce duration; incomplete records return null. Scheduled end never changes episodes. Rate limits and duplicate controls are separate: a user-level PostgreSQL row lock serializes report requests across backend instances. `(user_id, idempotency_key)` is unique. Identical retries return the same report identity, even if rate/cooldown limits are now reached; changes to location/kind/time/note return 409. Keys remain for as long as reports remain (no automatic purge). Current moderation state may change after review. An identical kind following the same user's latest accepted kind has a configurable cooldown; other people and their evidence are independent, including shared IP addresses. Accepted requests are limited per user per hour using database creation times, not a process-local limiter.

Configurable defaults: REPORT_RATE_LIMIT=20/hour; REPORT_BACKDATE_HOURS=24; REPORT_FUTURE_SECONDS=300; REPORT_COOLDOWN_SECONDS=600. The frontend retains the payload/key after an uncertain failure; clicking the same reporting action retries that payload. It only reports success after the backend confirms. Retry memory lasts while the dashboard remains mounted; it does not survive full reload. User history and evidence have an explicit refresh button.

Admins can accept, defer or reject observations with a required reason and optional candidate_event_id. Association requires matching location and remains provisional; it does not create an officially confirmed event. Audit captures the original observation, prior state, reason and decision. Moderation rebuilds only that reporter's personal episodes from accepted observations in deterministic observed/submitted/UUID order. It does not close other users' episodes. Pending out-of-order evidence is applied only after explicit review. Original observation kind/time/content are preserved.

## Run, migrate and verify

From repository root:

```bash
bash scripts/setup.sh
cd backend
.venv/bin/alembic upgrade head
.venv/bin/alembic check
.venv/bin/uvicorn app.main:app --reload --port 8000
```

In a second terminal: `npm run dev --prefix frontend`. Admin creation remains `backend/.venv/bin/python scripts/create-admin.py`. Setup seeds only the physically isolated fictional demo_areas; no operational source record is represented as verified demo data. Automated browser fixtures live solely in disposable test databases.

```bash
python3 scripts/test.py
backend/.venv/bin/ruff check backend
backend/.venv/bin/ruff format --check backend
npm run lint --prefix frontend
npm run format:check --prefix frontend
npm run build --prefix frontend
CHROMIUM_EXECUTABLE=/usr/bin/chromium python3 scripts/browser-test.py
```

The PostgreSQL runner creates a uniquely named database, checks empty upgrades and a 0001→head round trip before creating test records, then runs real API tests and Alembic metadata comparison. It drops only that disposable database. Downgrading 0003 refuses records with unknown source publication times because schema 0002 cannot represent them; it never invents a source timestamp. Back up populated development/deployment databases before changing schema.

Manual review: create a sourced notice as Admin → verify → publish → create explicit-area schedule → publish → check User notice board → report off → retry same payload → report restoration → refresh personal history and evidence → verify another user's still-off episode remains open. Test a stale Admin edit (409), withdraw the notice, and confirm it and linked schedules disappear from public reads. Review a rejected report and its revision audit. Repeat at mobile width.

No upload endpoint, external official feed, independently verified Sylhet dataset, or hosted deployment is included. Core phase features use the real backend; broader dashboard redesign remains outside this phase.

Validation for this phase: 32 backend tests passed against disposable PostgreSQL; three Chromium journeys passed (1440px, 390px authentication/location and the new Admin publication/User off-retry-restoration flow). Ruff lint/format, TypeScript lint, Prettier, Vite production build, development Alembic comparison and Git whitespace checks passed. One upstream Starlette/httpx deprecation warning remains. This verifies local behavior, not real-world source accuracy or external delivery.
