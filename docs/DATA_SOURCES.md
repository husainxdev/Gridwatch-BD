# Supplied directory integration — 2026-11-04

The user's `GridWatch_BD_Sylhet_Locations.sqlite` is retained byte-for-byte as [`data/sylhet-locations.source.sqlite`](../data/sylhet-locations.source.sqlite), SHA-256 `452a74777756002e59e39c36b4d47a91faccf764ae8006590aaaabe7cc8fb6a9`. It contains geographic/source reference data, not authentication, power reports or schedules.

- 428 portal records: 1 division, 4 districts, 41 upazilas, 339 unions, 1 city corporation and 42 general wards.
- 5,765 supplied Census 2022 records for Sylhet district: the original census_thana, ward_segment, mauza_segment, mahalla, village, municipality and cantonment kinds are preserved separately. They are **not** silently converted to current administrative units.
- 19 source links, 4 review-queue entries, 41 union-roster checks, 32 descriptive utility/locality references and 9 guide notes. Supplied guide/SQL text is data, never executable instructions.

Original divisional upazila/union rosters and SCC/other available sources were retrieved over verified HTTPS. 419 portal entries matched source names in the correct parent group or the prior independently reviewed city catalog. Nine remain unverified: seven Sadar unions with boundary/roster concerns, West Alirgaon and Silam whose local corroborating pages were unavailable. Review evidence, retrieval dates, response hashes and per-row decisions are in [`data/sylhet-locations.review.json`](../data/sylhet-locations.review.json). A match establishes the recorded administrative name/relationship, not surveyed boundaries or electrical coverage.

The supplied census PDF URL returned a 7,758,587-byte, 821-page PDF (SHA-256 `25939e8a529c98cd298bedcef19fedbd5a8315fc5a500e2f573d2daed5382ead`). The cited PDF page 164 rendered blank in this review. **Per-row PDF/page extraction remains unverified**; the user-supplied page numbers and codes are retained as claimed metadata. Historical results visibly say so and cannot be saved/reported against as current locations. English original labels remain English; limited Bangla search spellings are aids, not official translations or boundary evidence. The other three districts' village rows are absent from this extraction.

Utility references remain references only. No feeder, schedule, verified actual outage, household coordinates or live telemetry was inferred/imported. [Integration and checks](SUPPLIED-DIRECTORY.md).

---

## Earlier 45-record pilot evidence (historical)

# Current administrative catalog — 2026-11-04

A reviewed real administrative directory is now bundled at [`data/sylhet-city-locations.v1.json`](../data/sylhet-city-locations.v1.json): Sylhet Division → Sylhet District → Sylhet City Corporation → 42 general wards (45 records total). This does **not** establish electricity coverage, feeder/provider mappings, live power status, neighborhoods, or any outage schedule.

Original pages were successfully retrieved over verified HTTPS on 2026-11-04:

| Original publisher | URL | Facts imported |
| --- | --- | --- |
| Sylhet divisional commissioner's office | https://sylhetdiv.gov.bd/pages/static-pages/696cb9bfc4774958d7ba981e | Sylhet division and its Sylhet district membership |
| Sylhet City Corporation | https://scc.gov.bd/pages/static-pages/6922df09933eb65569e1f5f4 | City corporation identity and current summary of 42 wards |
| Sylhet City Corporation | https://scc.gov.bd/pages/static-pages/6922dcfd933eb65569e1310d | Independent current ward assignments, all 14 groups covering ward numbers 1–42 |

Review timestamp: **2026-11-04 10:54:45 UTC** (16:54:45 Asia/Dhaka). Source retrieval times, response SHA-256 hashes, short excerpts and ward-number groups are retained in the manifest. The SCC overview also contains historical prose about 27 wards; current 42-ward coverage is corroborated against the separate assignment page updated 13 September 2026. No outdated neighborhood/union boundary or officer contact information was imported.

Bangla/English display names and search aliases are curated spelling/translation aids, **not official administrative codes**. IDs are internal deterministic UUIDs. `Location.source_url` and `verified_at` preserve each initial source/date. Re-running an import does not refresh verification dates or overwrite later Admin changes. Read [the area repair report](AREA-SEARCH-REVIEW.md) and [normal startup](WEBSITE.md) for commands and preservation behavior.

The cloud network policy is now unrestricted/enforced (observed revision 30), allowing direct original-source research through the configured proxy. Earlier 403/503 and draft-only findings below are historical. District-root requests still returned 503, so those pages are not used as evidence; district membership is supported by the divisional source above. Search-engine snippets were not used as official facts.

No verified official outage notice, live official API, real feeder mapping or public deployment is supplied by this catalog. Electricity facts still require original notice/evidence review through the existing Admin workflow.

---

## Earlier research and limitations (historical record)

# Data sources, provenance and monitoring limits

Release preparation date: 2026-10-29. **No real Sylhet pilot boundary/provider, official notice or feeder-coverage dataset has been independently verified or loaded as operational facts in this handoff. No working official live electricity API is connected.**

## What is actually used

The later [populated local walkthrough](LOCAL-DEMO.md) seeds only a separate marked demo DB. All locations, review statuses, observations and evidence there are fictional, including the reserved example.com placeholder. They are not additions to verified Sylhet records. Re-running preserves original fixture timestamps. Normal configurations continue excluding demo notices/schedules/reports.

| Data | Actual provenance/status | Date/freshness meaning |
| --- | --- | --- |
| Official outage schedules | None supplied as verified real-world records. CRUD/publication is implemented and tested with fictional isolated fixtures. | Real publication/source dates remain unavailable until an Admin checks an original notice. Unknown publication date stays unknown. |
| Administrative hierarchy | Flexible typed location model and source-review workflow. No officially verified Sylhet import in the release. | Source URL, review status/time and GridWatch update time are separate; a location slug/UUID is not an official code. |
| Electricity offices/feeders | Separate source-backed registry workflow; no verified real provider mapping seeded. | Reviewed claims can be invalidated after edits. Administrative boundaries do not establish electrical coverage. Automatic feeder-to-schedule integration is not implemented. |
| Individual reports/history | Authenticated users' own connection observations. Local QA records are explicitly fictional. | Observation timestamp differs from submission/retrieval/update time. Server stores timezone-aware timestamps; UI uses Asia/Dhaka. |
| Verified outage events | Separate reviewed event model; no real verified event supplied here. | An event needs start/restoration evidence; a scheduled end never restores an actual event. Admin review is traceable, not automatically government confirmation. |
| Demo home areas | Two fictional rows in the physically separate `demo_areas` table via guarded development seed. | Never an availability feed, official location list or recorded actual outage. Normal production disables this endpoint. |
| Submission screenshots | Real locally rendered application captures from isolated QA accounts/fixtures. | Captured during the Sections 11–12 local tests; not a deployed site or historical proof of actual outages. |

Potential research portals already identified in scope are [BPDB](https://bpdb.gov.bd/), [Sylhet City Corporation](https://scc.gov.bd/) and [Sylhet district portal](https://sylhet.gov.bd/). These are **research starting points**, not citations for imported facts. No new source-content verification date is assigned to them in this release. Obtain the exact page/original notice, date, responsible office and named coverage before registering a verified pilot record. Do not confuse a city corporation with an upazila or a police jurisdiction with an administrative unit.

## Evidence rules

- Keep planned windows, raw reports, personal episodes and reviewed event records separate. Never manufacture events from schedules or use missing reports as proof of power availability.
- A user's restoration closes that user's eligible episode only. Latest-per-person summaries count the same person once in the selected observation window; they do not represent every household.
- Pending/rejected/demo observations follow the inclusion rules in [Sections 5–6](SECTIONS-5-6.md) and [Sections 7–8](SECTIONS-7-8.md). Future-clock-tolerated reports remain pending until review; out-of-order evidence does not silently rewrite original observations.
- Source links must use HTTPS and contain no username/password. The server does not fetch submitted URLs or authenticate their contents automatically. A human must verify the source; a green review badge is not independent official certification.
- Activity checks use current published, non-cancelled announcements with explicit/uncertain coverage and half-open interval union. “No matching announcement” never promises electricity.
- Personal history counts recorded episodes, keeps unknown bounds unknown, excludes open/incomplete durations from completed averages, clips ranges and splits completed intervals at Bangladesh midnight. It is not complete monitoring, area reliability or SAIDI/SAIFI.
- Dashboard polling defaults to 30 seconds, pauses/backoffs when hidden/offline/failing and labels old data stale. Fetch time does not change an old observation's time. No offline delivery or background reminder is claimed.

## Demo isolation and acceptance gate

The local demo creator provisions a **new** `gridwatch_demo_...` database and new private credentials, never resets the normal development database. Operational tables start empty; only the two fictional home demo rows are seeded. Use clearly labeled practice records on this isolated database for a presentation. Do not present their review workflow as real official verification.

A hosted disposable demo must have its own DB/secret set, backend `DEMO_INSTANCE=true`, matching frontend `NEXT_PUBLIC_DEMO_INSTANCE=true`, and private examiner-only Admin credentials. The application validates the DB namespace and shows a persistent warning; the operator must additionally verify physical/account isolation. Never publish a privileged password on a real-user environment. Publicly shared demo Admin capability isolation has not been implemented or authorized here.

Before claiming a real Sylhet pilot: verify original administrative/provider evidence, create only the small confirmed hierarchy, record source/review metadata and add an original source-named notice. No source dates, citations, feeder codes, confidence percentages or APIs should be invented to complete a submission field.

## Research follow-up — 2026-11-04

Canonical and `www` Sylhet district/BPDB requests returned 503, SCC returned 403. The BPDB proxy diagnostic reported upstream TLS certificate verification failure; verification was not disabled. No content/facts were imported from those responses. An alternative official-portal/document/search network draft was saved for platform review/publication and is not evidence of access or verification. The exact candidate hosts, observations and remaining verification procedure are in [the full review](FULL-REVIEW-2026-11-04.md).
