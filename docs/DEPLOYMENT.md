# Deployment guide — not yet executed

This is a deployment recipe, not a claim of a live service. Obtain a host/domain and a managed PostgreSQL database first. A real public launch also needs verified Sylhet pilot sources, secure SMTP delivery, backups, rate limiting and a security review. Avoid presenting fictional fixtures or unverified notices as live outages.

## Same-origin layout

Serve the built React app and `/api/*` on the same HTTPS origin. [The example Caddyfile](../deploy/Caddyfile.example) proxies API requests to a loopback Uvicorn process and proxies all other routes to the Next.js Node process on loopback port 5173. DNS must point to the host for Caddy's automatic HTTPS. Do not expose PostgreSQL, SMTP or Mailpit ports publicly. Do not copy local `.env` files or development database volumes to the server.

## Build and configuration

On a host with Python 3.12+, uv and Node 22+, install from a pinned commit:

```bash
cd /srv/gridwatch/backend
uv sync --frozen --no-dev
cd /srv/gridwatch/frontend
npm ci
npm run build
```

Place a root-readable `/etc/gridwatch/api.env` containing the following **names**, with host-specific secret values supplied through your deployment secret manager. Never commit this file:

```dotenv
DATABASE_URL=postgresql+psycopg://USER:PASSWORD@PRIVATE_DB_HOST:5432/gridwatch
JWT_SECRET=LONG_RANDOM_SECRET_AT_LEAST_32_CHARACTERS
APP_ENV=production
DEMO_ENABLED=false
CORS_ORIGINS=["https://gridwatch.example.org"]
FRONTEND_URL=https://gridwatch.example.org
SMTP_HOST=PRIVATE_SMTP_HOST
SMTP_PORT=587
SMTP_STARTTLS=true
SMTP_USERNAME=YOUR_SMTP_USER
SMTP_PASSWORD=YOUR_SMTP_SECRET
MAIL_FROM=no-reply@gridwatch.example.org
```

The adapter requires authenticated STARTTLS in production. Store SMTP credentials in deployment secrets, never source control. Local Mailpit is for development only.

With the production environment loaded, run `backend/.venv/bin/alembic upgrade head` as an explicit deployment step before restarting the API. Re-run only after a reviewed schema change and a backup. Configure the example systemd units for the API and Next.js frontend; Caddy terminates HTTPS and routes requests. Run `npm run start` from the built frontend directory (the service example uses this command). Set `GRIDWATCH_API_TARGET` at build time if changing the Next.js rewrite upstream; Caddy routes public `/api` directly to Uvicorn. Browser requests always stay same-origin. `NEXT_PUBLIC_*` values are public build-time configuration, never secrets. Do not enable `NEXT_PUBLIC_E2E_TEST` in deployed builds. The default `.next` build and isolated `.next-test` browser-test build are distinct.

## Live verification checklist

After DNS, TLS and services are ready, verify `/api/health/live`, `/api/health/ready` and the HTML shell over HTTPS. Register a throwaway account, log in, refresh, log out, request a password reset through a secure mail channel, and confirm the old token cannot be reused. Verify non-admin requests to admin routes return 403. Verify that no operational records or real pilot claims appear until sources are reviewed. Recheck mobile layout, access logs, backup restoration and ingress rate limits. Record the actual domain and test results for the submission package.

A real area must be verified by a person before entering official notices. No official feed, feeder mapping or provider access has been assumed by this repository.

## Authentication configuration

Use the same HTTPS origin for frontend and API; separate-site deployments are unsupported. See [Sections 3–4](AUTH-LOCATIONS.md) for exact cookie paths, CSRF and token lifetimes. `AUTH_RATE_LIMIT=60` / `AUTH_RATE_WINDOW_SECONDS=60` provide per-process limits only. Apply shared ingress limits before public exposure. Never log request bodies, Authorization headers, cookies or reset links. Current readiness requires schema `0006`. See [Sections 5–6](SECTIONS-5-6.md) for publication, reporting and migration rules.
