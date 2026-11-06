// Exercise the actual Next config without provider access or a public deployment.
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { transpileModule, ModuleKind } from "typescript";

const source = transpileModule(
  readFileSync(new URL("../next.config.ts", import.meta.url), "utf8"),
  { compilerOptions: { module: ModuleKind.ESNext } },
).outputText;
const keys = [
  "VERCEL",
  "NETLIFY",
  "CONTEXT",
  "COMMIT_REF",
  "GRIDWATCH_API_TARGET",
  "NEXT_PUBLIC_E2E_TEST",
  "RELEASE_REVISION",
  "VERCEL_GIT_COMMIT_SHA",
  "GRIDWATCH_LOCAL_DEMO",
  "NEXT_PUBLIC_DEMO_INSTANCE",
  "GRIDWATCH_TEST_BUILD",
  "GRIDWATCH_LOCAL_WEBSITE",
];
const original = Object.fromEntries(keys.map((key) => [key, process.env[key]]));
let run = 0;
async function config(env) {
  for (const key of keys) delete process.env[key];
  Object.assign(process.env, env);
  return (
    await import(
      `data:text/javascript;base64,${Buffer.from(source).toString("base64")}#case-${run++}`
    )
  ).default;
}
try {
  const base = {
    VERCEL: "1",
    GRIDWATCH_API_TARGET: "https://backend.example.com",
    VERCEL_GIT_COMMIT_SHA: "a".repeat(40),
  };
  const good = await config(base);
  const headers = await good.headers();
  assert(headers[0].headers.some((h) => h.key === "Strict-Transport-Security"));
  assert.deepEqual(await good.rewrites(), [
    {
      source: "/api/:path*",
      destination: "https://backend.example.com/api/:path*",
    },
  ]);
  for (const invalid of [
    { GRIDWATCH_API_TARGET: "" },
    { GRIDWATCH_API_TARGET: "http://backend.example.com" },
    { GRIDWATCH_API_TARGET: "https://user:secret@backend.example.com" },
    { NEXT_PUBLIC_E2E_TEST: "1" },
    { GRIDWATCH_LOCAL_DEMO: "1" },
    { NEXT_PUBLIC_DEMO_INSTANCE: "true" },
    { GRIDWATCH_TEST_BUILD: "1" },
    { GRIDWATCH_LOCAL_WEBSITE: "1" },
    { VERCEL_GIT_COMMIT_SHA: "" },
    { RELEASE_REVISION: "b".repeat(40) },
  ])
    await assert.rejects(config({ ...base, ...invalid }));
  const netlifyBase = {
    NETLIFY: "true",
    CONTEXT: "production",
    GRIDWATCH_API_TARGET: "https://backend.example.com",
    COMMIT_REF: "c".repeat(40),
  };
  const netlify = await config(netlifyBase);
  assert.equal(netlify.distDir, ".next");
  assert.deepEqual(await netlify.rewrites(), await good.rewrites());
  const netlifyHeaders = await netlify.headers();
  assert(
    netlifyHeaders[0].headers.some(
      (h) => h.key === "Strict-Transport-Security",
    ),
  );
  assert.equal(netlifyHeaders[1].source, "/api/:path*");
  assert(
    netlifyHeaders[1].headers.some(
      (h) => h.key === "Cache-Control" && h.value === "no-store",
    ),
  );
  for (const invalid of [
    { GRIDWATCH_API_TARGET: "" },
    { GRIDWATCH_API_TARGET: "http://backend.example.com" },
    { GRIDWATCH_API_TARGET: "https://backend.example.com/api" },
    { GRIDWATCH_API_TARGET: "https://user:secret@backend.example.com" },
    { NEXT_PUBLIC_E2E_TEST: "1" },
    { GRIDWATCH_LOCAL_DEMO: "1" },
    { NEXT_PUBLIC_DEMO_INSTANCE: "true" },
    { GRIDWATCH_TEST_BUILD: "1" },
    { GRIDWATCH_LOCAL_WEBSITE: "1" },
    { COMMIT_REF: "" },
    { COMMIT_REF: "wrong" },
    { RELEASE_REVISION: "b".repeat(40) },
    { CONTEXT: "deploy-preview" },
    { CONTEXT: "branch-deploy" },
  ])
    await assert.rejects(config({ ...netlifyBase, ...invalid }));
  await config({ ...netlifyBase, RELEASE_REVISION: netlifyBase.COMMIT_REF });
  const demo = await config({ GRIDWATCH_LOCAL_DEMO: "1" });
  assert.equal(demo.distDir, ".next-demo");
  const local = await config({});
  assert(
    !(await local.headers())[0].headers.some(
      (h) => h.key === "Strict-Transport-Security",
    ),
  );
  console.log(
    `${run} release-config cases passed: Netlify/Vercel HTTPS, source identity, no test/preview builds, rewrite and HSTS; no provider contacted.`,
  );
} finally {
  for (const key of keys) {
    if (original[key] === undefined) delete process.env[key];
    else process.env[key] = original[key];
  }
}
