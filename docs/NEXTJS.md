# Next.js frontend migration

The requested framework is **Next.js**, as clarified by the user. The frontend now runs Next.js 16.4.3 App Router with React, TypeScript (compiled to JavaScript), Tailwind CSS 4 and DaisyUI 5. FastAPI/PostgreSQL remain the backend. Vite, its plugin/config/HTML entry, and React Router have been removed from active dependencies and execution.

## How it works

- `frontend/app/layout.tsx` supplies Bengali metadata, locally packaged fonts, shared styles and the persistent provider/layout.
- Explicit App Router pages cover home, sources, notices, signup/login/reset, dashboard, Admin, activities, history and progress. Unknown paths return Next's 404. An error boundary offers retry without exposing internal exception text.
- `frontend/src/navigation.tsx` adapts existing link/search/navigation contracts to Next Link, navigation hooks and Next-integrated native History updates. This retains filters, browser back/forward and current UI components without a second router.
- Private data remains browser-fetched from FastAPI. Initial HTML is a loading shell; session refresh gates private views before rendering. Access credentials stay in browser memory and refresh cookies remain HttpOnly. No user data or tokens are passed through React Server Component props or server caches. This is not server-rendered personalized content or a no-JavaScript application.
- Browser requests always use relative `/api`. `next.config.ts` rewrites to the server-only `GRIDWATCH_API_TARGET` origin (default `http://127.0.0.1:8000`) and gives API responses `Cache-Control: no-store`. Same-origin cookie, CSRF and CORS rules are unchanged. API target changes require rebuilding production output.
- `NEXT_PUBLIC_POLL_INTERVAL_MS` replaces the former Vite polling variable. Public values are compiled at build time, not secrets. Existing Vite variables are no longer used.
- Production hosting needs a Node process (`next start`), not a static `dist` host. Caddy and frontend service examples are updated. Node 22.12+ is recommended; validation used Node 24.

## Existing Windows checkout

Keep your `.env` secrets and working PostgreSQL port, including 15432 if configured. Stop the old frontend with Ctrl+C before updating. In PowerShell:

```powershell
cd "$env:USERPROFILE\Gridwatch-BD"
git pull
npm.cmd ci --prefix frontend
docker compose up -d --wait db mail
cd backend
py -m uv sync --frozen --python 3.12
.\.venv\Scripts\python.exe -m alembic upgrade head
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload --port 8000
```

Keep that backend terminal open. In a second PowerShell:

```powershell
cd "$env:USERPROFILE\Gridwatch-BD"
npm.cmd run dev --prefix frontend
```

Open `http://localhost:5173`. Keep both terminals open. Do not pass Vite's removed `--strictPort` option. For a local production build instead:

```powershell
npm.cmd run build --prefix frontend
npm.cmd run start --prefix frontend
```

Port 5173 remains the default so existing trusted frontend/CSRF origins work. If changing the port, also update the backend's trusted frontend/CORS settings. No Next.js migration changes PostgreSQL credentials; migrations 0005–0006 belong to the Admin/planning work.

## Testing and production separation

The browser runner builds the actual Next.js production application into `.next-test`, starts `next start` against a disposable migrated PostgreSQL database and real FastAPI process, then removes the test database. It never uses a Vite server or the real user's database for fixtures.

Existing tests previously imported Vite source modules in the browser. They now use a narrowly scoped `window.__gridwatchTest` bridge enabled only by `NEXT_PUBLIC_E2E_TEST=1` in that isolated build. It exposes API actions, session acceptance/locking and date/poll helpers, never token getters or browser storage. Normal builds do not enable the bridge; do not set this variable for deployment. The `.next` production build stays separate from `.next-test`.

Run:

```bash
python3 scripts/test.py
CHROMIUM_EXECUTABLE=/usr/bin/chromium python3 scripts/browser-test.py
npm run lint --prefix frontend
npm run format:check --prefix frontend
npm run build --prefix frontend
npm audit --prefix frontend --audit-level=high
```

Omit `CHROMIUM_EXECUTABLE` when using Playwright's installed Chromium on Windows. The existing runner chooses Windows or Linux venv paths. Linux cloud execution does not establish a tested Windows runtime.

Validated in this cloud workspace: **50 backend tests**, **13 browser tests against `next build` / `next start`**, migration/model checks, strict TypeScript, formatting, production build and npm audit (zero reported vulnerabilities). The default build was also smoke-checked separately from the test build. See the review for exact commands and limitations.

## Manual checks

1. Signup/login, reload the dashboard, then open it in another tab; session restoration should work without token storage.
2. Search/select/save an area. Navigate between activities/history/dashboard, and use browser back/forward on filtered lists.
3. As Admin, publish a sourced schedule; as User, save an overlapping activity. Cancel the schedule and check the activity again.
4. Submit personal off/back observations; inspect clipped history and review changes without treating reports as whole-area evidence.
5. Logout and confirm both tabs lose protected access. Check an unknown URL displays the 404 page.

Real Sylhet sources, hosting/domain verification and external SMTP delivery remain prerequisites. No official/live integration is inferred from this framework migration. See [the implementation review](REVIEW-2026-10-29.md) for remaining boundaries and actual check results.
