# GridWatch BD — scope and decisions

## Release objective
A Bengali-first university project for understanding planned outages and community reports in one small Sylhet pilot. The seven-day sprint is a prioritization guide, not a delivery or production-readiness promise. Current increment: local application workflows implemented; real pilot evidence and hosted deployment pending.

## Pilot and source register
No pilot boundary, provider, feeder mapping, official notice or API has been verified yet. Do not publish a real-area coverage claim. The two seeded areas are fictional UI fixtures, physically isolated in `demo_areas`. Sylhet is the intended region, not a claim of verified coverage.

Before enabling operational data, select one neighborhood/ward with the project owner, verify its administrative parent chain against authoritative government records, identify its actual electricity provider, and retain a public original notice URL or original document with provenance. Record publisher, publication time, retrieval time, scope, reviewer and verification time. Re-check corrections and cancellations. A notice covering a feeder does not prove a neighborhood belongs to that feeder. Do not scrape, infer or invent mappings. Sources are pending; there are no citations to present as verified.

| Candidate evidence | Current state | Acceptance requirement |
| --- | --- | --- |
| Administrative area hierarchy | Pending | Authoritative record and human-reviewed parent links |
| Provider service coverage | Pending | Provider evidence for selected pilot |
| Official outage notice | Pending | Original URL/document, publication timestamp and scope |
| Restoration evidence | Pending | Explicit observed restoration with source and reviewer |
| Official API | Not connected | Documented access, permission, schema and failure behavior |

### Pilot research status (26 October 2026)

The intended pilot is **one ward or neighborhood within Sylhet City Corporation**, selected only after its boundary and provider are evidenced. No ward has been designated as verified. The following hostnames were attempted through the cloud proxy as candidate official-source locations: `bpdb.gov.bd`, `scc.gov.bd`, and `sylhet.gov.bd`. Each HTTPS CONNECT returned **403 Domain forbidden** under the current restricted egress policy; no page content, ownership claim, ward list, provider coverage or notice was obtained. These are research targets, **not citations or confirmed authorities**. The same root and `www` hostnames have been added to the environment configuration draft for review. After that policy is applied, check the actual sites, their redirects and source provenance before choosing the pilot. A source being accessible does not itself establish that a ward is served by a particular feeder.

To mark a pilot verified, record: the precise ward/neighborhood label; its parent chain and publication URL; provider coverage evidence; the reviewer and review date; and an original notice whose stated scope actually matches that area. If an official notice only names a feeder, do not map it to the ward without separate provider evidence. Keep status unknown when any link is missing.

## User flows
1. Visitor chooses an area → sees unknown/known status, separated schedules and reports, provenance and freshness → opens original notice.
2. User registers/signs in → saves locations → reports power off/back/still off for their own connection → receives confirmation without implying area-wide restoration.
3. User enters a planned activity with date/time/duration → sees overlap with announced schedules, with uncertainty warning → optionally changes time. No schedules means no announced conflict found, not guaranteed electricity.
4. User browses history → only recorded verified events contribute to actual outage duration; planned schedules remain separate.
5. Admin signs in → reviews sources and area mappings → manages notices/schedules → reviews evidence and records actual outage/restoration → searches, filters, sorts and pages listings.

## Data semantics and time
- Store instants as PostgreSQL `timestamptz`; accept timezone-aware inputs in future APIs. Display Asia/Dhaka (UTC+6), never infer from server timezone.
- Location nodes have typed parent links. Urban and rural paths differ; e.g. district → city corporation → ward → neighborhood vs district → upazila → union → village. No fixed five-column location table.
- Future location service must validate allowed parent types, reject longer cycles and require evidence before verification. SQL currently prevents self-parenting only.
- Schedules describe plans and require a notice. No clock-driven restoration. Cancelled/superseded schedules do not count as active conflicts.
- Reports describe a person's connection. Missing, stale or conflicting reports leave area status unknown. Cooldown/dedup rules belong to section 6; unique per-user request keys already prevent identical request replay at storage level.
- Verified events require a reviewer and start evidence. Restoration requires its own evidence and timestamp. History never substitutes scheduled time for actual time.
- Demo fixtures must never enter operational tables or aggregate counts. Production disables demo endpoint and seeding.

## Architecture
Next.js App Router + React + TypeScript (JavaScript output); Tailwind CSS v4 + DaisyUI v5; React Icons; React Hot Toast. Self-hosted Bengali font avoids a runtime font CDN dependency. FastAPI + SQLAlchemy + Alembic with PostgreSQL 17. Public endpoints include health, development-only demo areas, notices, schedules, locations, reports and recorded events. Authenticated endpoints provide reports and saved areas; admin endpoints manage reviewed operational records.

Operational routers use typed request schemas and bounded pagination with whitelisted sort keys. A future official-source adapter should normalize incoming material to reviewable drafts and never publish it directly. Service-layer separation and an independent security review remain deployment work.

## Authentication implementation and remaining hardening
Bcrypt password hashing with a documented 72-byte input limit; normalize and uniquely constrain emails. Short-lived JWT access tokens held in memory. Random refresh tokens stored hashed in `refresh_sessions`; rotate on every refresh, detect replay and revoke the family. Use HttpOnly, Secure, SameSite cookies scoped to refresh endpoints, explicit trusted origins and CSRF protection. Logout revokes sessions and clears cookies. Password reset uses hashed, expiring, single-use tokens, generic responses and rate limiting; reset invalidates sessions. Never log tokens. Admin permission checks must run on the server for every protected operation. No demo users or login credentials are seeded. Local SMTP uses Mailpit; public mail delivery requires configuration. Ingress rate limiting and independent security review remain before public deployment.

## Non-goals for this sprint
Nationwide coverage, outage prediction, emergency dispatch, SMS/push delivery, automatic feeder inference, a guaranteed official API, and automatic trust from report counts. No production-ready claim without security, deployment and operational evidence.
