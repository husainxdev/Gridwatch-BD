# Data sources, provenance and monitoring limits

Release preparation date: 2026-10-29. **No real Sylhet pilot boundary/provider, official notice or feeder-coverage dataset has been independently verified or loaded as operational facts in this handoff. No working official live electricity API is connected.**

## What is actually used

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
