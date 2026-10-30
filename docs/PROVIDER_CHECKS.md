# Provider evidence and unresolved account checks

Checked 2026-10-29. Selected path: **Vercel Next.js + Render FastAPI + Render PostgreSQL 17**. No alternative platform was newly configured. Historical Caddy/systemd examples are retained for existing work, not selected or verified for this release.

The direct `render.com/docs/*`, `render.com/schema/render.yaml.json` and `vercel.com/docs/*` requests returned **403** under this environment's outbound policy. No proxy bypass or disabled TLS was used. The following publicly published **official provider source repositories** were retrieved instead:

| Source | Pinned source revision | Confirmed scope |
| --- | --- | --- |
| [Render FastAPI example README](https://github.com/render-examples/fastapi/blob/f829276c68503f7afae195c3e3f778f085242cb0/README.md) and [service example](https://github.com/render-examples/fastapi/blob/f829276c68503f7afae195c3e3f778f085242cb0/render.yaml) | `f829276c68503f7afae195c3e3f778f085242cb0` | Native Python service, binding `0.0.0.0`, provider `$PORT`, build/start commands, manual service creation and disabling auto-deploy. |
| [Vercel Next.js framework definition](https://github.com/vercel/vercel/blob/84878e532142f0ac584953695658b324eb9e5b80/packages/frameworks/src/frameworks.ts) | `84878e532142f0ac584953695658b324eb9e5b80` | `nextjs` detection, `@vercel/next` adapter, Next build command/default output and public `NEXT_PUBLIC_` prefix. The app uses the adapter, not static SPA output. |
| [Render CLI generated API types](https://github.com/render-oss/cli/blob/4c382c29f64ddf2e7cd968d3b4487c05b1650cdd/pkg/client/types_gen.go) | `4c382c29f64ddf2e7cd968d3b4487c05b1650cdd` | PostgreSQL version 17, build/start/pre-deploy API fields and auto-deploy controls exist. |
| [Render Blueprint validation command](https://github.com/render-oss/cli/blob/4c382c29f64ddf2e7cd968d3b4487c05b1650cdd/cmd/blueprintvalidate.go) | same | Account/workspace-backed schema, semantic/plan and resource-conflict validation. We have no such account access and do not claim that validation. |
| Next.js 16.4.3 bundled `docs/.../headers.md` and route-handler guide | installed locked package | Security headers, API rewrites and release-info route syntax. Production/development builds are tested locally. |

**Not verified:** actual account entitlement, selected plan, fees, quotas, sleep/cold-start behavior, request/build timeouts, runtime patch availability, backups/retention, outbound SMTP restrictions, provider proxy address policy, live certificate chain and successful remote deployments. The example's `plan: free` and API plan enums are not a free-tier eligibility/price guarantee. Do not create billable resources based on this document. The owner must inspect the current account console/official docs and authorize any costs separately.

No Vercel/Render account tools, ready outbound identities, hosted-service secrets or authorized service URLs were available in the environment. Git repository access is available; it does not confer hosting-account access. `deploy/provider-settings.json` deliberately records null live origins and no plan. Provider account validation and live verification remain blocked, not marked successful by local JSON consistency checks.
