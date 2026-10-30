# Populated local demonstration

All supplied locations, announcements, observations, reviews and event evidence are **fictional**. A separate `gridwatch_demo_...` database, explicit backend mode and persistent Bengali banner keep this walkthrough distinct from normal records. Normal configuration/data are preserved. No official Sylhet source or live feed is supplied.

## Windows: update once, then double-click

Docker Desktop, backend `.venv` and frontend dependencies must already be installed, as in the owner's working setup. Preserve the configured PostgreSQL port, including 15432.

In **PowerShell**:

```powershell
cd "$env:USERPROFILE\Gridwatch-BD"
git pull --ff-only
```

Open the project folder in File Explorer and double-click **`START-DEMO.cmd`**. The batch file invokes the backend venv directly; its contents are not intended to be pasted into PowerShell. Alternatively, from the project folder in either shell:

```text
py scripts/start-local-demo.py
```

The launcher starts Docker Desktop if needed on Windows and the existing Compose services, creates a **new** private demo DB/profile once, migrates it, provisions unique Admin/User credentials and seeds records transactionally. It starts loopback-only servers and opens **http://127.0.0.1:5174/login**. Keep its terminal open. Ctrl+C stops its servers, preserving its DB. Normal servers on 8000/5173 use a different build directory and remain separate.

Open the login file locally in Notepad, away from a projector/public screen:

```text
notepad .private\demo-ready\credentials.json
```

Use the record with role `user` for Dashboard or `admin` for management. These accounts belong to this machine's new demo DB. Git does not copy another machine's database/passwords. There is no committed/default privileged password. Restrict access to the private folder with Windows account ACLs; Linux 0600 checks do not establish Windows ACL behavior.

## What appears after login

| Fixture | Contents |
| --- | --- |
| Locations | Nine fictional nodes; separate city/ward/neighborhood and upazila/union/village branches |
| Saved areas | Default neighborhood A and optional B for each login account |
| Notices | One public practice notice, one private draft, one withdrawn |
| Schedules | Two overlapping announced windows, one cancelled window, one private draft |
| Reports/history | Ten fictional observations, five independent personal episodes across the accounts/simulated neighbor; completed, open and unknown-start cases |
| Activities | Class with a 60-minute union conflict; an exact-end-boundary activity without overlap |
| Reviewed event | Separate practice event with explicit fictional start/restoration evidence, independent of schedules |
| Audit | Dataset manifest and per-record fixture provenance; no official source claim |

The simulated neighbor is inactive and cannot log in. User history contains two completed 30-minute episodes and one incomplete restoration observation. A completed episode crosses Bangladesh midnight with a 10/20-minute split. Recent User restoration and neighbor still-off produce mixed evidence, never area-wide availability. **Review statuses simulate the workflow, not government verification.** The reserved `example.com` placeholder is explicitly not an official citation.

Open Dashboard, Notices, Activities and History. In Activities open **কাল্পনিক ডেমো: অনলাইন ক্লাস** for a fresh check. In History select the demo neighborhood or search `Demo A`. Admin sees the private draft and pending observation. New notices/reports in this instance remain marked demo server-side.

## Persistence, reset and troubleshooting

- Re-running preserves accounts, passwords, edits and original timestamps. The manifest makes repeated insertion a no-op. Printed counts describe the initial fixture set, not subsequent user records.
- Windows are relative to **first seed time** and naturally become past/stale. Old observations are not refreshed and scheduled end does not restore an episode.
- For fresh practice times, stop the demo, then run `py scripts/start-local-demo.py --directory .private/demo-2`. This creates a new DB; old/normal records are not reset.
- If 8001/5174 are occupied, close the earlier demo terminal. The launcher refuses to kill an unknown existing process.
- `--prepare-only` prepares without servers; `--no-browser` starts without opening the browser.
- Partial config or nonempty operational data without a seed marker is refused. Choose a new private directory; do not delete user records. Seed failure rolls back its transaction.

## Verification and boundaries

Real local PostgreSQL/Linux Chromium checks cover both roles, reload, defaults, data display, draft privacy, conflicts/history, mobile overflow and logout at 390/1440px. Backend tests cover mode/namespace/actual-connection guards, normal evidence exclusion, duplicate seed refusal/idempotency and independent numeric expectations. Normal application regressions run separately.

Native Windows batch/process cleanup needs the owner's execution check. External email is disabled in this demo. Real Sylhet sources/public deployment remain unverified. During this change, official Sylhet district/BPDB requests returned 503 and SCC returned 403; no official record was imported from those responses. No public deployment or purchase is part of this workflow.

Actual follow-up checks:

| Check | Result |
| --- | --- |
| `backend/.venv/bin/python scripts/test.py` | 59 passed, one existing Starlette/httpx deprecation warning; fresh/populated migrations and no model drift |
| `CHROMIUM_EXECUTABLE=/usr/bin/chromium backend/.venv/bin/python scripts/browser-test.py` | 24 passed; two dedicated demo tests skipped here because they require the separate demo server/profile |
| With the demo launcher running: `GRIDWATCH_DEMO_CREDENTIALS=ABSOLUTE_PRIVATE_FILE CHROMIUM_EXECUTABLE=/usr/bin/chromium node frontend/node_modules/@playwright/test/cli.js test --config frontend/playwright.config.ts populated-demo.spec.ts` | Two real-backend demo journeys passed, 390px and 1440px |
| `npm run check:release --prefix frontend` | 10 configuration cases passed, including demo build separation and rejection on Vercel |
| `npm run format:check --prefix frontend`, `npm run lint --prefix frontend`, `npm run build --prefix frontend` | Passed; strict route/TypeScript checks and normal production build |
| `backend/.venv/bin/ruff check backend scripts`, `backend/.venv/bin/ruff format --check backend scripts`, `git diff --check` | Passed |
| Real launcher preparation, re-run, Ctrl+C and restart | Private dataset created; repeat does not reset it; Linux child servers close and existing database containers remain |

An initial browser assertion used a label not present in the UI; it was corrected to the actual conflict heading. Next automatically added its demo type directories to tsconfig; these paths are committed/formatted so launching the demo does not repeatedly rewrite tracked configuration. No application error or validation was suppressed to obtain passing results.
