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
- Forces demo endpoints/fixtures and browser helpers off at runtime. On a genuinely empty directory, it imports the reviewed 45-record Sylhet administrative catalog. It does not create accounts, notices, schedules, observations, feeder mappings or history.
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

The administrative catalog now uses three successfully retrieved original government pages. It contains the division/district/city corporation and 42 general wards only. No neighborhood-to-ward or electricity/feeder mapping is inferred, and no official live outage API is connected. See [current evidence](DATA_SOURCES.md).

## Before public publishing

Use [DEPLOYMENT.md](DEPLOYMENT.md) and [DASHBOARD_SETUP.md](DASHBOARD_SETUP.md) for actual hosting accounts, HTTPS frontend/backend URLs, persistent PostgreSQL, trusted same-origin `/api` routing, external SMTP, backups, ingress rate protection and live acceptance. Configure `DEMO_INSTANCE=false`, `DEMO_ENABLED=false`, `NEXT_PUBLIC_DEMO_INSTANCE=false`; remove all browser/local build flags. Public production rejects demo mode rather than hiding its banner.

The public interface now contains no project-progress checklist or demo CTA. `/help` explains real workflows; `/privacy` describes actual fields and retention limits. Legacy `/progress` shows the same help content for old links. Missing real records display actionable empty states instead of fake status cards.

## Existing directory: merge reviewed wards once

On an empty directory the normal launcher imports the real administrative catalog automatically. If you already have custom locations, default startup leaves them untouched. To explicitly merge the reviewed directory, preserving existing matching identities and all human edits, run:

```text
C:\Users\USER\Gridwatch-BD\START-WEBSITE.cmd --import-catalog
```

The importer uses one transaction and the same advisory locks as Admin hierarchy mutations. Existing records are reused and never silently re-verified or renamed. A conflicting type/parent stops and rolls back the import. No passwords, accounts or electricity facts are added. Normal repeated startup does not re-create a removed individual ward in a nonempty directory.

For a hosted operator, use the reviewed backend configuration and actual database name, then run `backend/.venv/bin/python scripts/import-location-catalog.py --expected-database ACTUAL_NAME` as a controlled one-time step. The command reads the bundled reviewed manifest; it never fetches arbitrary submitted URLs.

Search examples that work within this catalog: `সিলেট`, `Ward 1`, `ওয়ার্ড ১`, `ওয়ার্ড ০১`. You can also select the city shortcut and choose any of the 42 ward buttons. A neighborhood name such as আম্বরখানা is not mapped to a ward without an original verified source.

## Supplied full source directory

The normal launcher now applies migration `0007` and imports the checksum-reviewed supplied SQLite directory once into PostgreSQL. It adds 428 portal/source records and keeps 5,765 historical census records in a separate read-only reference branch at **http://localhost:5173/areas**. Existing 45 pilot IDs and all account/report data remain; 419 portal identities have source checks, nine stay unverified. Census references are never automatically linked to current ward/report targets.

On an older populated local database, the launcher automatically creates a private PostgreSQL custom-format backup and checksum receipt under `.private/backups/` before the controlled schema upgrade. Backup creation failure stops the upgrade; no database reset is used. Each backup's restoration is not automatically performed or claimed. Production upgrades remain a separate operator-controlled migration/backup procedure. Do not publish the backup files.

From CMD or PowerShell, close earlier API/frontend terminals, pull, and use `C:\Users\USER\Gridwatch-BD\START-WEBSITE.cmd`. Open **এলাকার পূর্ণ তালিকা** or the location picker's larger-directory link. Search `বালাগঞ্জ` in portal records, or `Ambarkhana` / `আম্বরখানা` in the explicitly labelled 2022 reference branch. Details and exact source links are preserved.

## Search and matching service versions

`/areas` now searches both source branches by default as you type; results retain their current/historical labels. Name parts, ancestor names, Bengali digits and English case are supported, with exact names before broad ancestor matches. Filters, breadcrumbs, keyboard access and URL-restored searches work against PostgreSQL. Missing Bengali translations or unprovided villages cannot be found under invented names.

A 404/422 on the directory API means the web/API versions may differ, not that no area exists. Stop both earlier server terminals with Ctrl+C, pull the matching code, then run START-WEBSITE.cmd. Startup verifies the unified search directly and through the frontend proxy before opening the website. It never kills unrelated processes or resets existing records.
