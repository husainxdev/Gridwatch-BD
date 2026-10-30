# GridWatch BD — university submission record

**Overall status: partially prepared; live submission incomplete.** Sections 1–12 are implemented/local-verified within the documented scope. Section 13 deployment and required live parts of Section 14 remain blocked by missing authorized hosting/email access. Do not submit this as a fully deployed project yet.

| Required item | Value | Acceptance classification |
| --- | --- | --- |
| Project name | GridWatch BD — Bangladesh Load Shedding & Power Outage Management | Implemented and verified |
| Frontend repository | https://github.com/husainxdev/Gridwatch-BD/tree/main/frontend | Implemented and verified (existing authorized monorepo/path) |
| Backend repository | https://github.com/husainxdev/Gridwatch-BD/tree/main/backend | Implemented and verified (same monorepo/path) |
| Live frontend | **Not available — no verified deployment URL** | Blocked |
| Live backend | **Not available — no verified deployment URL** | Blocked |
| Deployment configuration | Vercel Next.js + Render FastAPI/PostgreSQL; `frontend/vercel.json`, `deploy/provider-settings.json`, release scripts | Implemented but externally unverified |
| Schema | Alembic `0006`; no new schema change in release preparation | Implemented and locally verified |
| Local private Admin/User accounts | Separate newly created `gridwatch_demo_...` database; unique generated passwords; browser login/reload/roles/logout checked | Implemented and locally verified; deployed accounts externally unverified |
| Hosted demo accounts | Not created/tested on a deployed service | Blocked |
| Real pilot/source data | No verified real Sylhet dataset/official API | Blocked on source verification |
| External reset email | Real SMTP adapter locally tested against a controlled loopback sink; no verified external sender/delivery | Implemented but externally unverified |
| Provider backup/restore | Local dump/restore/restart proven; no provider DB access | Implemented but externally unverified |
| README, data-source/deployment guides, architecture/viva/demo script | Files linked below | Implemented and locally verified |
| Public demo Admin / bounded public reset service | No intentionally public privileged credentials or data-reset endpoint | Not implemented; private-only evaluation chosen |
| Automatic official API/notifications/uploads | Outside the implemented first-release scope | Not implemented; do not advertise |

Repository ownership/visibility has not been changed. The remote and frontend/backend paths were checked with Git access; examiner access to a private repository must be granted by the owner. The exact preparation commit is recorded in the final handoff and Git history. The actual deployed commit remains unavailable until both `/release-info` and `/api/health/live` match the chosen full source SHA on real HTTPS services.

## Implemented features

- Bengali-first Next.js/React/TypeScript/Tailwind/DaisyUI frontend, FastAPI and persistent PostgreSQL schema.
- Signup/login, bcrypt byte-limit validation, short JWT access, rotating hashed refresh sessions, server-side role/ownership checks, logout/revocation and password-reset workflow.
- Flexible location hierarchy/search/source review, saved/default areas and bounded paging.
- Source-reviewed notice/schedule lifecycle, cancellation/revisions, individual off/back/still-off reports and independent personal episodes.
- User/community dashboards with source/time/stale/unknown labels; Admin listing/moderation/version/audit workflows and separate office/feeder-claim registry.
- Saved activities and fresh half-open/union conflicts; private history with clipping, Bangladesh daily splitting and honest incomplete evidence.
- Local core/permission/concurrency/numeric/migration/browser/accessibility checks, private demo preparation and guarded release/backup tools. See [QA matrix](QA-SECTIONS-11-12.md) and [release evidence](RELEASE-STATUS.md).

## Private credential handoff

No privileged password is committed or printed in this document. The cloud workspace's ignored `.private/local-demo/credentials.json` holds the **local-only** generated Admin/User pair; `.private/local-demo/backend.env` holds its sensitive local configuration. They are private 0600 files in this Linux workspace, not GitHub artifacts or live credentials. Obtain them through an owner-authorized private file handoff; do not paste them into an issue, screenshot, public report or presentation.

For another machine, run the [local demo procedure](DEMO_SCRIPT.md) to create a new isolated DB and new passwords there. A Git pull does not copy the cloud database or private files. For a hosted demo, the owner must first provision a separate marked DB, privately create the accounts and verify the real site; fill the two live URL rows only after acceptance. Do not reuse personal credentials. Revoke old demo sessions and create a new isolated namespace for a reset; never reset production.

## Live acceptance checklist — all currently unverified

For a populated local presentation, [the launcher](LOCAL-DEMO.md) generates an independent private pair in `.private/demo-ready/credentials.json` and fictional walkthrough records. It does not supply deployed credentials or verified electricity data.

Record actual URL/source SHA/date/browser/results before changing these statuses:

- [ ] Frontend HTTPS, certificate/security headers, deep-link reload and intended backend proxy.
- [ ] Direct/proxied health/readiness `0006`, matching frontend/backend source commit and demo label.
- [ ] Dedicated Admin/User login; reload refresh; logout clears cookies/revokes access; direct User→Admin API denied.
- [ ] Area selection, save/default and persistence after reload plus actual restart/redeploy.
- [ ] Private draft → reviewed/published notice/schedule → User display → revision/cancellation reflected.
- [ ] User A off/retry, User B off/back, A still off/back; personal histories remain separate.
- [ ] Saved activity conflict changes after schedule update; history numbers/daily boundaries/source age are correct.
- [ ] Authorized SMTP sender delivers to a controlled recipient; reset single use and previous-session invalidation.
- [ ] Mobile/keyboard/failure states, no secret-bearing diagnostics, real backup restored into an isolated DB.

No test report is published as a real observation. Use only dedicated isolated demo data for write checks; cancel/archive the created evidence and preserve audit history. Existing personal/production records must not be reset or removed.

## Submission package

- [README](../README.md): scope, architecture, links, setup/run and checks.
- [Deployment and operations](DEPLOYMENT.md): one selected provider path, configuration, migration/backup/rollback and blockers.
- [Data sources](DATA_SOURCES.md): actual evidence, demo isolation and missing real-world verification.
- [Presentation/demo/viva](DEMO_SCRIPT.md): a suggested 5–7 minute walkthrough, diagrams and offline-hosting fallback.
- [Release status](RELEASE-STATUS.md): verified local results versus missing deployment evidence.
- [Curated real application screenshots](screenshots/README.md): isolated fictional QA captures, not mock/generated/live-outage images.
