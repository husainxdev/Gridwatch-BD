# Netlify frontend + Render backend

The owner selected Netlify on 6 November 2026. This is the current frontend hosting path. The existing FastAPI/PostgreSQL backend stays on Render. No Netlify site, assigned public origin, provider authentication or hosted acceptance has been established from this workspace.

## Owner dashboard steps

1. Sign in at https://app.netlify.com/ with GitHub. Select **Add new project / Import an existing project**, then GitHub and the existing `husainxdev/Gridwatch-BD` repository. Grant access to that repository if it is not listed. Do not upload a build folder manually.
2. Select production branch `main`. The repository-root `netlify.toml` declares base `frontend`, build `npm run build`, publish `.next`, Node 22 and development build dependencies. Netlify automatically installs its current OpenNext adapter for Next.js; do not pin the legacy runtime or enable static export. No SPA `/* -> /index.html` rule is needed.
3. Obtain the actual Render backend HTTPS origin from its service dashboard. In Netlify environment variables set `GRIDWATCH_API_TARGET` to that origin, with no `/api` suffix, credentials, query or trailing path. Set `NEXT_PUBLIC_DEMO_INSTANCE=false`. Select Builds and Functions scopes if the dashboard offers scopes. Do not put `DATABASE_URL`, `JWT_SECRET`, SMTP credentials or a Neon API key in Netlify's frontend environment.
4. Leave frontend `RELEASE_REVISION` **unset**: Netlify's read-only `COMMIT_REF` supplies the build source SHA. If you explicitly set RELEASE_REVISION, it must match COMMIT_REF and must be changed for each release. Remove `NEXT_PUBLIC_E2E_TEST`, `GRIDWATCH_TEST_BUILD`, `GRIDWATCH_LOCAL_DEMO` and `GRIDWATCH_LOCAL_WEBSITE`. These flags reject hosted builds instead of exposing fixtures.
5. Keep deploy previews/branch deploys disabled for this setup. Next config deliberately rejects non-production Netlify contexts because the backend trusts one exact frontend origin. A future preview environment needs its own trusted configuration/database; do not widen credentialed CORS to `*` or arbitrary `*.netlify.app` hosts.
6. Save the project and record its actual stable `https://…netlify.app` origin. A URL may be assigned before a successful build; it does not mean the backend works. Do not guess a domain from the project name. A first deploy may fail until the actual backend URL is set.
7. In Render set `FRONTEND_URL` to that exact Netlify HTTPS origin, with no trailing slash, and `CORS_ORIGINS` to a JSON array containing only that origin. Use APP_ENV=production, DEMO_ENABLED=false and DEMO_INSTANCE=false. Complete the PostgreSQL, signing-secret, SMTP and controlled schema/import steps in DEPLOYMENT.md. Deploy the same source commit on both services.
8. Require `/api/health/ready` on the backend to report schema `0007`, then trigger the Netlify production deploy. Open the site's `/release-info`; it must identify the same full source SHA as the backend's `/api/health/live`. Check `/api/health/ready` and `/api/directory/summary` through the Netlify domain too.

If either service needs the other's origin before starting, create both project configurations first, record their assigned actual origins, then finish settings and deploy. Do not substitute example domains or weaken production guards to make an initial build green.

## What runs where

- Netlify hosts the Next.js application using its automatic OpenNext adapter.
- Next's `/api/:path*` rewrite proxies to the Render `/api/:path*` endpoint. The browser stays on the Netlify origin. HttpOnly refresh/CSRF cookies, POST requests and Authorization headers must be checked on the actual hosted proxy.
- PostgreSQL remains a persistent hosted PostgreSQL database; MongoDB is not a schema replacement. Render or Neon may be used after reviewing the actual chosen plan and limits. The separate Neon agent setup is not required when using Render PostgreSQL.
- Missing original outage evidence remains unknown. Administrative and historical source rows are not invented power-status observations.

## Hosted acceptance before announcing availability

Run from an authorized operator environment, with actual public origins and deployed source SHA:

```text
backend/.venv/bin/python scripts/live-smoke.py --frontend ACTUAL_NETLIFY_HTTPS_ORIGIN --backend ACTUAL_RENDER_HTTPS_ORIGIN --expected-revision ACTUAL_FULL_COMMIT
```

This smoke check is read-only. Also verify signup/login, refresh after reload, logout/session invalidation, saved/default area persistence, approved notice changes, report ownership, activity conflicts, history and reset-token single use. Confirm real reset email delivery to an owner-controlled address, multiple Set-Cookie forwarding/clearing, no API caching, CSRF rejection for wrong origins and persistence after backend restart. Never publish fictional outage observations in the real-user database.

The local production browser suite is real FastAPI/PostgreSQL/Next integration, but does not certify Netlify's adapter, provider cookies, cold starts, plan limits or live deployment. Those require actual provider access and URLs.

## Sources checked

Official docs retrieved 6 November 2026:

- https://docs.netlify.com/build/frameworks/framework-setup-guides/nextjs/overview.md — App Router, rewrites, route handlers and automatic OpenNext adapter; no adapter pin recommended.
- https://docs.netlify.com/build/configure-builds/environment-variables.md — NETLIFY=true, production CONTEXT, COMMIT_REF source metadata.

The docs' broad Next.js compatibility statement is not a hosted acceptance result for this repository's specific version.

## Local validation for this change

- `npm run check:release --prefix frontend`: **29 cases passed**, including Netlify production HTTPS, COMMIT_REF matching, preview/test/demo rejection, rewrite and cache/security headers; legacy Vercel/local cases retained.
- `NETLIFY=true CONTEXT=production COMMIT_REF=<synthetic-test-SHA> GRIDWATCH_API_TARGET=https://backend.example.com npm run build --prefix frontend`: passed. Reserved example.com origin used only for this configuration/build test; no backend availability claim.
- Started that build locally on loopback: release-info contained the synthetic Netlify COMMIT_REF; three deep-link shells had HSTS/security headers; missing page returned 404. This used Next's local server, not Netlify's deployed adapter.
- `npm run lint --prefix frontend` and `npm run format:check --prefix frontend`: passed.
- `backend/.venv/bin/python scripts/test.py tests/test_release.py tests/test_website.py`: **14 passed**, one existing upstream Starlette/httpx deprecation warning; disposable PostgreSQL migration/upgrade checks passed with no drift.
- `CHROMIUM_EXECUTABLE=/usr/bin/chromium backend/.venv/bin/python scripts/browser-test.py auth-locations.spec.ts release-preparation.spec.ts`: **4 passed** against real local FastAPI/PostgreSQL and a production Next build.
- Ruff check/format (64 files), local provider-manifest validation and git diff checks passed.

No deployed Netlify adapter, hosted cookie forwarding, provider account, SMTP delivery or external origins were verified. Prior full application test evidence remains in FINAL-RELEASE-REVIEW.md and is not re-labelled as a new full-suite run.
