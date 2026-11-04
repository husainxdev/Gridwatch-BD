# Normal website and publishing workflow

The normal website uses the existing Next.js/React/TypeScript/Tailwind/DaisyUI frontend and FastAPI/PostgreSQL backend. The owner requested a public-facing interface instead of the old fictional walkthrough. No real location, official schedule or availability observation is invented to fill empty screens.

## Windows: one launcher, both CMD and PowerShell

Close previously running API/frontend launch terminals with Ctrl+C. Keep Docker's data volumes. From either CMD or PowerShell:

```text
git -C "C:\Users\USER\Gridwatch-BD" pull --ff-only
C:\Users\USER\Gridwatch-BD\START-WEBSITE.cmd
```

Open **http://localhost:5173/**. Keep that terminal open; Ctrl+C stops only its own API/frontend child processes. Docker data and existing configuration remain. Backend binds loopback port 8000, Next binds loopback 5173. A separate `.next-website` build directory prevents the historical demo's `.next-demo` from conflicting with this server.

The launcher:

- Preserves `.env`, `backend/.env`, custom PostgreSQL ports and existing normal accounts/records. It never changes a user's password or overwrites secrets.
- Starts Docker Desktop from its actual per-user/system path when needed on Windows, then starts the existing Compose PostgreSQL and Mailpit services.
- Checks that the mapped Compose database port matches the configured local PostgreSQL URL, and that the schema is current. It refuses hosted/production, demo, test, restore and browser databases.
- Forces demo endpoints/fixtures and browser helpers off at runtime. It does not run any seed or create accounts, notices, observations or history.
- Requires your own account through registration. Password reset uses configured SMTP; standard local setup catches messages at **http://127.0.0.1:8025**. This is a local mailbox, not external delivery.
- Runs locally in development mode. It does not make your PC reachable to the public internet or claim HTTPS/provider acceptance.

If dependencies are absent, run from the repository root (CMD or PowerShell):

```text
py -m uv sync --project backend --frozen --python 3.12
npm.cmd ci --prefix frontend
.\backend\.venv\Scripts\python.exe scripts\start-website.py --check-only
```

Both root `.env` and `backend/.env` are generated with random local-only secrets only if both are absent. Partial setup is refused. Never replace existing secrets to resolve a connection problem. The existing 15432 mapping, if configured, must stay consistent in Compose and `DATABASE_URL`. A port conflict stops with instructions; the launcher never kills unrelated processes.

Linux/macOS equivalent: `backend/.venv/bin/python scripts/start-website.py`. Run `--no-browser` to suppress automatic browser opening.

## Administrator

From the repo root on Windows:

```text
.\backend\.venv\Scripts\python.exe scripts\start-website.py --create-admin
```

The CLI asks for email, name and password using a hidden password prompt. It creates an Admin only in the selected normal database and refuses an existing email. No default credentials or privileged public signup exist. Start the website afterward and log in with that account. Public registration always creates a normal User.

The older fictional accounts stay in their separate database. They do not log in to this site. The launcher does not convert fake notices/report history into real records or erase the old database.

## Older schema / safe upgrades

The launcher runs the existing controlled migration helper. If a populated database is behind head `0006`, it refuses to upgrade without a backup reference. From the repo root, first run a private backup with a new filename:

```text
.\backend\.venv\Scripts\python.exe scripts\db-archive.py backup --expected-database gridwatch --file .private\before-website.dump --local-compose
```

Verify the backup/restore using [deployment operations](DEPLOYMENT.md); then run `scripts/start-website.py --backup-reference YOUR_RECORDED_BACKUP_REFERENCE`. Use the actual database name if it differs from `gridwatch`. Never reset a volume, drop a normal database or silently downgrade to make setup pass. No schema changes are introduced by this UI work.

## Add real records

1. Verify a small administrative chain and original public source. Preserve the exact source URL, publishing/verification times and administrative types. Police areas and feeder coverage are not administrative levels.
2. In Admin, create the actual hierarchy and source registry entries, then verify only records supported by the original source. Do not use fictional example URLs as verification.
3. Save the original notice as a draft. Review its text, coverage and times, then verify and publish it. Link a schedule to that notice and publish separately. Revisions/cancellations preserve the traceable history.
4. Users may then save supported areas and submit their own connection observations. A schedule never creates an actual outage. An absence of reports never establishes available power.

The current environment still receives 403/503 from the permitted official Sylhet/BPDB/SCC sources. No real Sylhet import or government live API is claimed. The saved broader research network draft was not activated as of this change.

## Before public publishing

Use [DEPLOYMENT.md](DEPLOYMENT.md) and [DASHBOARD_SETUP.md](DASHBOARD_SETUP.md) for actual hosting accounts, HTTPS frontend/backend URLs, persistent PostgreSQL, trusted same-origin `/api` routing, external SMTP, backups, ingress rate protection and live acceptance. Configure `DEMO_INSTANCE=false`, `DEMO_ENABLED=false`, `NEXT_PUBLIC_DEMO_INSTANCE=false`; remove all browser/local build flags. Public production rejects demo mode rather than hiding its banner.

The public interface now contains no project-progress checklist or demo CTA. `/help` explains real workflows; `/privacy` describes actual fields and retention limits. Legacy `/progress` shows the same help content for old links. Missing real records display actionable empty states instead of fake status cards.
