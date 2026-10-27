# Sections 3–4: authentication and locations

The browser uses the real FastAPI service through `/api`. Development uses Vite's proxy; deployment must serve the frontend and API on one HTTPS origin. API request/response schemas are at `/docs` and `/openapi.json` on the running backend. Roles are serialized as `user` / `admin`.

## Authentication contract

| Method and path | Input / result |
| --- | --- |
| POST `/api/auth/register` | email, password, display_name; creates USER and signs in (201). Extra fields, including role/user_id, are rejected. |
| POST `/api/auth/login` | email, password; access_token, token_type and public user profile |
| GET `/api/auth/me` | Bearer token; current active user's public profile |
| POST `/api/auth/refresh` | Refresh cookie, exact trusted Origin and X-CSRF-Token; rotates session |
| POST `/api/auth/logout` | Same CSRF requirements; revokes session family and clears cookies (204) |
| POST `/api/auth/password-reset/request` | email; generic 202 for known/unknown accounts, including transport failure |
| POST `/api/auth/password-reset/confirm` | token, password; consumes token, revokes all sessions, requires a new login |

Emails use EmailStr normalization, trimmed lowercase storage and database case-insensitive uniqueness. Passwords must be 8–72 **UTF-8 bytes**, including Bangla characters; bcrypt never truncates. Public signup rejects privileged extra fields. The operator creates an admin using `backend/.venv/bin/python scripts/create-admin.py`; it prompts privately for the password and refuses to change an existing account's role.

Access JWTs use HS256 and `JWT_SECRET` (minimum 32 characters). Required signed claims: sub, sid, type=access, iat, exp; the database is authoritative for role and active status. Access lifetime is **15 minutes**. Every protected request checks the user and refresh-session row, so logout, refresh rotation, disablement and password reset invalidate earlier access immediately. This deliberately costs a database read rather than treating JWTs as irrevocable until expiry.

Refresh tokens are 48 random bytes encoded URL-safe; only SHA-256 hashes are stored. Tokens expire **7 days after each issuance**, including rotation (rolling lifetime, no absolute family maximum). Each row records user, family, expiry, revocation and replacement. User/token row locks serialize rotation and password-reset/session revocation. Reusing a replaced token revokes the whole family. Concurrent refreshes using the same token produce one 200 and one 401; reuse also invalidates the winner. This strict policy requires signing in again when independent browser tabs race. The frontend deduplicates refresh within one tab and retries eligible failed requests only once; cross-tab refresh coordination is not implemented.

Reset tokens contain 48 random bytes, expire after **20 minutes**, and are hashed and consumed under a row lock. Reset revokes all existing sessions and does not sign the user in. Links use only configured `FRONTEND_URL`; tokens travel in `#token=...` fragments, which browsers do not send to HTTP access logs. The reset page removes the fragment from history and posts the token in the request body. Never enable request-body/Authorization/Cookie logging or capture reset links in screenshots. Validation responses omit raw submitted input. Application handlers do not log credentials or tokens.

## Cookies, CSRF, errors and limits

Refresh cookie: `gridwatch_refresh`, HttpOnly, host-only, Path=/api/auth, SameSite=Strict, Max-Age=604800. CSRF cookie: `gridwatch_csrf`, readable by the frontend, host-only, Path=/, same lifetime and SameSite. Both use Secure in production; local HTTP development omits Secure. Logout expires both at their original paths. Access tokens remain in module memory, never localStorage/sessionStorage. Protected pages wait for startup refresh. A failed refresh clears local session state; failed logout does not show success.

Refresh and logout require an Origin exactly equal to `FRONTEND_URL` and a matching CSRF cookie/header. CORS uses `CORS_ORIGINS` with explicit origins and credentialed requests; wildcard origins are rejected. Local access should use `http://localhost:5173` consistently. Split-site frontend/API hosting is unsupported by this cookie topology; use a same-origin reverse proxy. The frontend uses `credentials: same-origin`.

Errors use `detail`; schema errors also include `fields` with field, message and code (no input values). Conflicts return 409, invalid input 422, absent/expired authentication 401 and missing permissions 403. Database exceptions do not expose SQL or connection strings.

`AUTH_RATE_LIMIT=60` and `AUTH_RATE_WINDOW_SECONDS=60` bound POST auth requests **per process, per client IP, per endpoint** with HTTP 429/Retry-After. This includes signup, login, reset and refresh. It does not coordinate workers, survive restarts or replace ingress protection. Configure deployment-wide ingress limits and trusted proxy forwarding; do not accept arbitrary client-supplied forwarding headers. Shared NAT clients share one allowance.

## Email development and production

`docker compose up -d db mail` starts the local Mailpit SMTP adapter at localhost:1025; view development mail at http://localhost:8025. Use the app's forgot-password form and open the captured link. No external delivery occurs. Integration tests substitute an in-memory SMTP capture adapter and test token consumption without logging it.

Production requires SMTP_HOST/PORT, SMTP_STARTTLS=true, SMTP_USERNAME, SMTP_PASSWORD and MAIL_FROM from a secret manager. The adapter validates TLS via the system trust store. Missing/insecure configuration returns a generic service-unavailable error for every account; transport failure returns the same 202 response as unknown accounts and rolls back the reset record. A 202 response is not proof of email delivery. No production SMTP credentials or delivery verification are available in this workspace.

## Location and ownership contract

| Endpoint | Behavior |
| --- | --- |
| GET `/api/locations` | roots_only, parent_id, search, kind, status; page>=1, page_size 1–100 |
| GET `/api/locations/{id}` | Details, aliases, source URL, verification and update time |
| GET `/api/locations/{id}/children` | Immediate children, paginated |
| GET `/api/locations/{id}/ancestors` | Root-to-parent ordered breadcrumbs |
| POST/PUT/DELETE `/api/admin/locations[/{id}]` | Admin create/update/delete; referenced deletion returns 409 |
| POST `/api/admin/locations/{id}/verify` | Admin review with HTTPS source_url |
| GET `/api/saved-areas` | Only current user's areas |
| POST/DELETE `/api/saved-areas/{location_id}` | Save/remove current user's area; duplicate save is idempotent |

Search supports Bangla/English names, aliases and exact UUID. Listings sort by English name then UUID for stable pagination. Status is verified/unverified. The supported tree is division → district, then either upazila → union → village → neighborhood, or city_corporation → ward → neighborhood. These are separate administrative types, not police or electricity jurisdictions. Extend the documented parent map with verified evidence before importing a different structure.

Self-parenting, descendant cycles, invalid parent types and changes that invalidate existing children are rejected. Tree edits are serialized with a PostgreSQL transaction advisory lock. Duplicate normalized names are blocked within parent/type, including root records; aliases do not establish a separate identity. API names use NFKC and collapsed whitespace, while database indexes additionally enforce lower/trim uniqueness. Updates clear verification and supersede associated announced schedules. Children, reports, saved areas, schedules and verified events block deletion. Electricity offices/feeders are not inferred from this hierarchy.

Saved-area ownership comes exclusively from the authenticated user; clients cannot choose a user_id. The composite database primary key prevents duplicates. Only verified locations may be saved/reported. Cascading selection clears dependent choices; obsolete requests are cancelled, search includes ancestor context, and valid selection remains while navigating the app. A full reload restores authentication and saved areas; the current picker selection is intentionally in memory.

No verified Sylhet data has been added. Browser fixtures are explicitly fictional and exist only in a disposable test database; development demonstration records remain in the separate demo_areas table.

## Migration and checks

```bash
cd backend
.venv/bin/alembic upgrade head
.venv/bin/alembic check
cd ..
python3 scripts/test.py
backend/.venv/bin/ruff check backend
backend/.venv/bin/ruff format --check backend
npm run lint --prefix frontend
npm run format:check --prefix frontend
npm run build --prefix frontend
# Install Chromium once if not already available:
cd frontend
npx playwright install chromium
cd ..
python3 scripts/browser-test.py
# Or use system Chromium:
CHROMIUM_EXECUTABLE=/usr/bin/chromium python3 scripts/browser-test.py
```

Migration 0002 adds aliases, normalized unique indexes and refresh replacement linkage. PostgreSQL 15+ is required for NULLS NOT DISTINCT (Compose uses 17). Existing duplicate normalized records cause migration failure instead of silently deleting/merging user data; review them before retrying. Back up populated deployments first. Tests create unique disposable databases and never reset the development database. Backend checks cover an empty upgrade and a 0001→0002 upgrade after round-trip downgrade. Browser tests use separate ports 18000/15173 and fictional location fixtures, and stop their servers/drop only their own database.

Manual review: register → inspect user dashboard → choose a tree branch/search alias → save/remove area → reload session → logout → login → request reset in Mailpit → reset → confirm old login fails and new login succeeds. Repeat on mobile, verify USER receives 403 at admin APIs, and verify another user cannot see the saved area. Check invalid-origin refresh returns 403. Admin review must precede any real source verification.

Validation recorded for this phase: 27 PostgreSQL backend tests; two Chromium journeys at 1440px and 390px (including delayed concurrent 401 handling); backend Ruff lint/format; frontend TypeScript strict/unused-code checks, Prettier and production build. Backend tests emit one upstream Starlette/httpx deprecation warning. No external delivery or public deployment was tested. Frontend `lint` uses the TypeScript compiler; ESLint is not configured.
