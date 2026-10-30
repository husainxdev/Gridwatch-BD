export const dynamic = "force-static";
export function GET() {
  const candidate =
    process.env.RELEASE_REVISION || process.env.VERCEL_GIT_COMMIT_SHA || "";
  const revision = /^[0-9a-f]{40}$/.test(candidate) ? candidate : "unversioned";
  return Response.json(
    {
      service: "gridwatch-web",
      revision,
      instance_mode:
        process.env.NEXT_PUBLIC_DEMO_INSTANCE === "true" ? "demo" : "pilot",
    },
    { headers: { "Cache-Control": "no-store" } },
  );
}
