# Selected release path — prepared, not publicly deployed

**Status:** Vercel frontend + Render native Python backend + persistent Render PostgreSQL 17. No live URLs or successful provider deployment exist in this handoff. Review [provider evidence and unverified limits](PROVIDER_CHECKS.md). Current local evidence is in [the release handoff](RELEASE-STATUS.md), not a claim of live verification.

The app is now Next.js App Router, as explicitly requested by the user. Vite's `dist`, React Router SPA fallback and `VITE_API_BASE_URL` are not used. Keep this monorepo; provider frontend root is `frontend`, backend service root is the repository root. Historical self-host examples are retained but are not the selected deployment.

## 1. Account prerequisites and billing boundary

Use existing authorized Vercel/Render projects and a persistent PostgreSQL instance, or let the owner review/create them. No service purchase, plan upgrade, domain transfer or repository visibility change is authorized by preparation. Record the actual selected plan/price, PostgreSQL storage retention, sleep/cold-start and timeout behavior from the current account before release. Availability is account-specific and currently unverified.

Reserve/select the Vercel project's actual production origin, obtain the Render service's actual HTTPS origin and choose the database **before final release**. Enter those actual values below; do not treat examples/placeholders as working domains. Configure only the stable production frontend origin; preview-domain login is unsupported until explicitly configured as a separate test environment.

## 2. Exact service settings

The machine-readable companion is [`deploy/provider-settings.json`](../deploy/provider-settings.json). It is an operator settings manifest, not a claim that provider account/billing/schema validation ran.

| Component | Settings |
| --- | --- |
| Vercel | Root `frontend`; framework `Next.js`; Node 22+ supported by the locked app (local verification used Node 24); install `npm ci`; build `npm run build`; leave output on the Next.js default `.next`/adapter. No static export, no `dist` and no custom SPA fallback. `frontend/vercel.json` pins install/build/framework. |
| Render API | Root repository `.`; Python 3.12 (select a supported 3.12 native runtime in Render; the build also explicitly requests 3.12; record the actual patch and verify the venv exists after deploy); build `pip install uv==0.12.23 && uv sync --project backend --python 3.12 --frozen --no-dev`; start `backend/.venv/bin/python scripts/serve.py`; health `/api/health/ready`; **one instance, one Uvicorn worker**, no reload. |
| Controlled pre-deploy | `backend/.venv/bin/python scripts/release-migrate.py --expected-database "$EXPECTED_DATABASE_NAME"`. Confirm pre-deploy access on the selected plan. If unavailable, run the same one-shot command in an authorized operator environment **before** switching traffic; never move it into each worker's startup. |
| Render PostgreSQL | Persistent PostgreSQL 17, appropriately private network/firewall access, database credentials in provider secrets; explicit TLS query setting. No application filesystem database or uploads. Select an actual plan/retention policy in the account. |

Disable automatic production deployment until account configuration and smoke verification are complete. No CI job deploys anything, and PR checks receive no production credentials. On Render use manual deploy/auto-deploy disabled. Configure Vercel Git deployment policy in the account or deploy the selected immutable commit manually. Do not automatically deploy untrusted PRs with production secrets.

## 3. Frontend settings and same-origin authentication

Set in Vercel **Production** settings, then rebuild:

- `GRIDWATCH_API_TARGET`: actual Render HTTPS origin, with no path/query/userinfo. Server-side rewrite target; never a database URL or signing key. Vercel builds reject a missing/insecure target.
- `RELEASE_REVISION`: full 40-character source commit, matching the backend. The release-info handler also supports provider `VERCEL_GIT_COMMIT_SHA`; configure/verify the system variable if relying on it.
- `NEXT_PUBLIC_DEMO_INSTANCE=false` for a real pilot. Use `true` only for a separate disposable demo DB matching backend `DEMO_INSTANCE=true`.
- Optional `NEXT_PUBLIC_POLL_INTERVAL_MS=30000`. No secrets in `NEXT_PUBLIC_*`.
- Never set `NEXT_PUBLIC_E2E_TEST` or `GRIDWATCH_TEST_BUILD` on a deployed project. Vercel refuses the test-helper flag.

Browser requests stay on **frontend `/api/*`**. Next rewrites to Render over HTTPS. Backend refresh cookies have no Domain attribute, so forwarded Set-Cookie belongs to the frontend origin: Secure, HttpOnly refresh token, SameSite Strict, Path `/api/auth`; readable CSRF cookie at `/`. The frontend's existing `credentials: same-origin` is correct for this topology. Cross-site direct browser API calls are not the supported setup.

Set backend `FRONTEND_URL` to the exact frontend HTTPS origin and `CORS_ORIGINS` to a JSON list containing **only that origin**. Origin + double-submit CSRF defenses remain active. Verify actual proxy Origin and Set-Cookie preservation, refresh after reload, logout-cookie deletion and revoked access on the deployed origin. Do not weaken CSRF/CORS or put refresh tokens in browser storage to work around a failure.

Next preserves fingerprinted asset caching and caches only public HTML/loading shells, not personalized server props. `/api/*` is no-store and backend private API responses are `private,no-store`. Headers include nosniff, frame denial, referrer/permissions policy and a compatible CSP restricting frames/objects/base URL; it is not a complete nonce-based script CSP. Verify provider HTTPS/HSTS in the real response before acceptance. Direct `/dashboard`, `/notices`, `/reset` navigation/reload uses App Router routes and is tested locally.

## 4. Backend secrets and production guards

Store values only in provider-managed secrets. The following are **names/placeholders**, not usable credentials:

```dotenv
APP_ENV=production
DATABASE_URL=REPLACE_WITH_PROVIDER_POSTGRESQL_URL_AND_TLS_OPTIONS
JWT_SECRET=REPLACE_WITH_SECURE_RANDOM_SIGNING_SECRET
FRONTEND_URL=REPLACE_WITH_EXACT_HTTPS_FRONTEND_ORIGIN
CORS_ORIGINS=["REPLACE_WITH_EXACT_HTTPS_FRONTEND_ORIGIN"]
RELEASE_REVISION=REPLACE_WITH_FULL_40_CHARACTER_GIT_COMMIT
EXPECTED_DATABASE_NAME=REPLACE_WITH_ACTUAL_DATABASE_NAME
DEMO_INSTANCE=false
DEMO_ENABLED=false
DB_POOL_SIZE=3
DB_MAX_OVERFLOW=2
DB_POOL_TIMEOUT=10
DB_POOL_RECYCLE=300
AUTH_RATE_LIMIT=60
AUTH_RATE_WINDOW_SECONDS=60
SMTP_HOST=REPLACE_WITH_AUTHORIZED_SMTP_HOST
SMTP_PORT=587
SMTP_STARTTLS=true
SMTP_USERNAME=REPLACE_IN_PROVIDER_SECRET_MANAGER
SMTP_PASSWORD=REPLACE_IN_PROVIDER_SECRET_MANAGER
MAIL_FROM=REPLACE_WITH_VERIFIED_SENDER
```

`postgres://` and `postgresql://` provider URLs normalize to SQLAlchemy `postgresql+psycopg://`; existing encoded passwords are preserved. Production requires explicit `sslmode=require`, `verify-ca` or `verify-full`. **`require` encrypts transport but does not prove hostname identity**; prefer `verify-full` with the provider's trusted CA/hostname after confirming their certificate instructions. Configure `sslrootcert`/certificate files securely when necessary. Actual Render TLS connectivity/chain is unverified without credentials/network access.

Pool maximum = 3 + 2 = **5 connections per process**, plus temporary migration/operator connections; size the selected DB accordingly. The release entry point handles provider `PORT`, requires production configuration, derives/checks a full source commit, and runs one worker without access-body/token logging. `/api/health/live` exposes only status/service/revision/instance mode; readiness checks database/schema `0006` without diagnostics.

Proxy headers are **not trusted by default**. Configure `TRUSTED_PROXY_IPS` only from the actual provider's verified ingress networks; arbitrary `*` trust is rejected. Without trusted forwarding, the process-local limiter may group users by proxy address rather than actual visitor IP. No per-visitor or deployment-wide rate guarantee is claimed. Before a public launch verify provider forwarding policy and deploy shared ingress limits for both proxy and direct-backend exposure. Keep a single backend instance until shared rate protection is verified.

Missing SMTP configuration produces an honest 503; transport failures return the same conditional generic reset response without claiming delivery. Production SMTP requires authenticated STARTTLS. Test only an owner-controlled recipient after sender verification; never use the local in-memory test sink or expose development reset links publicly.

## 5. Controlled migrations, backup and recovery

Never copy development volumes/`.env` to production. Never seed real production with QA fixtures. Before changing an existing database confirm provider/environment/DB name, record a backup and restore result, and identify schema compatibility/rollback risk.

The migration command checks the explicit DB name, takes a PostgreSQL advisory lock and uses one controlled Alembic connection. A fresh empty DB may upgrade directly; an existing non-current schema requires `--backup-reference` or `MIGRATION_BACKUP_REFERENCE`. A no-op current schema does not rerun migrations. A reference is an operator record, **not independent verification of the provider backup**. Keep backup/restore proof beside it privately.

From an authorized operator environment with PostgreSQL **17 client tools**, provider secrets in the environment and TLS/connection access configured:

```bash
backend/.venv/bin/python scripts/db-archive.py backup --expected-database ACTUAL_DB_NAME --file /private/gridwatch-release.dump
backend/.venv/bin/python scripts/release-migrate.py --expected-database ACTUAL_DB_NAME --backup-reference VERIFIED_BACKUP_RECEIPT_REFERENCE
```

The backup helper supplies native PG connection variables privately instead of putting a password-bearing URI in arguments. Archives are custom-format, exclusive-create, private 0600 files with a SHA-256 receipt. Backups contain private records/password hashes: encrypt them in a separate authorized backup store, restrict access and set retention. Do not commit, attach publicly, or log them. Native Windows ACL protection must be checked by the operator; chmod alone is not an ACL certification.

To test a restore, create a **fresh empty** isolated database named `gridwatch_restore_...`, provide that target's authorized env and run:

```bash
backend/.venv/bin/python scripts/db-archive.py restore --expected-database gridwatch_restore_UNIQUE_NAME --file /private/gridwatch-release.dump
```

The script checks the archive against its private SHA-256 receipt, refuses a populated target or a non-restore namespace, uses `--exit-on-error` and never cleans/drops existing tables. Verify schema and expected records, then upgrade that isolated restored DB with the backup reference and run private smoke checks. Record results before marking a backup restore-verified. Local Compose-only tests use `--local-compose`, which verifies loopback host/port mapping and never targets Render.

**Actually tested locally:** custom dump/restore of populated `0003`, preservation of user/location/saved-area references, safe upgrade to `0006`, wrong-target/backup-gate/nonempty-restore refusal and process restart/session/default persistence. This does not verify provider backups or a Render redeploy. No upload feature exists, so no permanent file-upload storage is configured.

## 6. Release and real-site acceptance

1. Record `git rev-parse HEAD`, clean source, successful local/CI checks and the selected account settings. `scripts/release-preflight.py --manual-provider-setup --output artifacts/preflight.json` checks sanitized configuration/presence only; it never deploys or verifies account authority.
2. Configure persistent DB, TLS, pool bounds and provider secrets. Use a separate marked DB for a private disposable demo; do not expose a shared Admin on real-user data.
3. Execute the controlled migration/pre-deploy once. Deploy Render from the exact revision; inspect health/revision and sanitized logs.
4. Build/deploy Vercel from the same revision with the actual HTTPS backend origin and matching demo label. Confirm deployment policy/limits in the account.
5. Run the following only with the **actual assigned URLs**:

```bash
backend/.venv/bin/python scripts/live-smoke.py --frontend ACTUAL_HTTPS_FRONTEND_ORIGIN --backend ACTUAL_HTTPS_BACKEND_ORIGIN --expected-revision FULL_COMMIT
```

It checks valid HTTPS, safe same-origin redirects, frontend/deep-link shells, security headers, direct/proxied readiness, matching source revisions and instance-mode labels. It performs a few read-only GETs; **it does not verify login, email, write journeys or persistence**. Do not substitute localhost output for this result.

6. Use dedicated private demo/test accounts on an isolated hosted demo. Execute the A–F journey checklist in [submission acceptance](SUBMISSION.md): roles/direct API 403, refresh/logout/cookies/CSRF, saved/default reload, notice publication/revision/cancel, independent reports, fresh activity conflict/history and controlled-recipient reset/single use. Confirm Asia/Dhaka times, sources, mobile/error states and no secret-bearing console/network/server diagnostics. Never send real fake outage reports. Cancel/archive only verification records created for this purpose; preserve audit history and never reset real users.
7. Restart/redeploy the actual backend and confirm a known saved/default record and session policy persist. Record actual domains, revision, time/browser and results. Until these pass, Sections 13–14 and the live submission are **partial/blocked**.

## 7. Operations and rollback

Inspect Render runtime/deploy logs and Vercel build/function logs for the recorded revision; do not enable SMTP debug, request-body, Authorization/cookie or reset-link logging. Restart through the service dashboard; state belongs in PostgreSQL, not the ephemeral app filesystem. Cold-start, sleep, timeout and retention properties must come from the selected actual plan, currently unknown.

Revert application code by selecting a previously verified immutable provider deployment/commit after checking schema compatibility. This phase still targets schema `0006`; a prior code revision may require the normalized psycopg URI and environment it supports. **Application rollback does not reverse migrations.** Never automatically run `alembic downgrade` on real data. For incompatible changes, keep traffic off, restore into an isolated new DB, validate and plan a controlled cutover rather than overwriting the original.

Rotate database/SMTP credentials through provider secrets and restart affected pools/services. Rotate signing keys privately; when revocation is required, use an authorized DB maintenance session to revoke active `refresh_sessions` before resuming access. Rotating only JWT signing material does not erase valid hashed refresh sessions. Revoke exposed demo sessions and provision a new isolated demo namespace/credentials; do not reuse personal passwords or print passwords in logs.
