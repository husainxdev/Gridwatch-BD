# Publish the normal GridWatch BD website

Use the existing `husainxdev/Gridwatch-BD` repository, branch `main`. This guide is for real accounts and reviewed administrative data. It does not publish fictional outages or test accounts. No hosted service or external email delivery has been verified from this workspace.

## 1. Persistent PostgreSQL

Select an existing supported PostgreSQL service, or create one after reviewing its current cost, retention and backup limits. A PostgreSQL-compatible hosted service such as Neon can be used; MongoDB cannot replace this application's SQL schema. Free plan availability and continued retention depend on the provider. Keep `DATABASE_URL` in provider secrets, never in the frontend or chat. Production requires an explicit appropriate TLS `sslmode`; see DEPLOYMENT.md.

## 2. Render backend

Connect the repository and select Python 3.12, root directory `.`. Disable automatic deployment until configuration and migrations are ready.

- Build: `pip install uv==0.12.23 && uv sync --project backend --python 3.12 --frozen --no-dev`
- Start: `backend/.venv/bin/python scripts/serve.py`
- Health: `/api/health/ready`
- Pre-deploy: `backend/.venv/bin/python scripts/release-migrate.py --expected-database "$EXPECTED_DATABASE_NAME"`

If the selected plan has no pre-deploy/shell access, use an authorized operator environment for the same one-time migration before serving traffic. Never run migrations from every worker. Set `APP_ENV=production`, `DEMO_INSTANCE=false`, `DEMO_ENABLED=false`, database URL, exact database name, a new strong random JWT signing secret, full release commit SHA, trusted frontend HTTPS origin and explicit CORS allowlist. Use backend/.env.example and DEPLOYMENT.md for all settings. Configure actual trusted proxy addresses; do not use wildcard forwarding trust. Readiness must report schema **0007**.

## 3. Vercel frontend

Import the same repository, root `frontend`, Next.js framework, `npm ci`, `npm run build`, default output directory. Set server-only `GRIDWATCH_API_TARGET` to the actual assigned Render HTTPS origin. Set `RELEASE_REVISION` to the exact full deployed source commit (must match Vercel's source SHA). Set `NEXT_PUBLIC_DEMO_INSTANCE=false`. Remove `GRIDWATCH_TEST_BUILD`, `NEXT_PUBLIC_E2E_TEST`, `GRIDWATCH_LOCAL_DEMO` and `GRIDWATCH_LOCAL_WEBSITE`. Deploy, then use its actual stable HTTPS origin in the backend's `FRONTEND_URL` and single-entry `CORS_ORIGINS` array. Cookies use the same-origin `/api` proxy, Secure and the documented SameSite/Path settings.

## 4. Import reviewed area identities

After migrating the actual expected database, run in the authorized backend/operator environment:

```text
backend/.venv/bin/python scripts/import-location-catalog.py --expected-database ACTUAL_DATABASE_NAME
backend/.venv/bin/python scripts/import-supplied-directory.py --expected-database ACTUAL_DATABASE_NAME
```

These transactional, repeatable imports preserve existing identities and human edits. They do not create users, notices, schedules, reports or feeder coverage. The 2022 census branch remains a historical reference; nine current portal records still require administrative review. Confirm `/api/directory/summary` and `/api/directory?branch=all&search=Ambarkhana` through the frontend domain.

## 5. Admin, mail and acceptance

Create your own Admin with the controlled CLI in DEPLOYMENT.md using its hidden password prompt. No public Admin signup or default Admin password exists. Configure an authorized real SMTP sender for password reset; Mailpit and the development adapter do not deliver mail to external users. Verify delivery to an owner-controlled address. Without that check, password-reset delivery remains a launch blocker.

Run `scripts/live-smoke.py` with the actual HTTPS origins using its `--help` arguments. Complete the authenticated acceptance checklist in SUBMISSION.md: signup/login, saved/default area persistence, logout invalidation, approved notice publication, independent personal reports, activity conflicts, history and single-use password reset. Check behavior after a real backend restart and validate a private backup/restore. A green health endpoint alone does not establish these journeys.

Record the actual frontend/backend origins, immutable source SHA, provider limits, test results and backup location. Tokens, passwords, database URLs and cookies stay in secure provider settings. Service names and public HTTPS origins may be shared for verification. Live publishing remains unverified until these checks run on the hosted services.
