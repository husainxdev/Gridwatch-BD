import type { NextConfig } from "next";
import path from "node:path";

const netlify = process.env.NETLIFY === "true";
const hosted = netlify || process.env.VERCEL === "1";
if (netlify && process.env.CONTEXT !== "production") {
  throw new Error(
    "Netlify deploy previews require a separate trusted backend; only production context is configured",
  );
}
const apiTarget = process.env.GRIDWATCH_API_TARGET || "http://127.0.0.1:8000";
const url = new URL(apiTarget);
if (
  !["http:", "https:"].includes(url.protocol) ||
  url.username ||
  url.password ||
  url.search ||
  url.hash ||
  url.pathname !== "/"
) {
  throw new Error(
    "GRIDWATCH_API_TARGET must be an HTTP(S) origin without credentials, path or query",
  );
}
if (
  hosted &&
  (!process.env.GRIDWATCH_API_TARGET || url.protocol !== "https:")
) {
  throw new Error(
    "Hosted deployments require the explicit HTTPS backend origin",
  );
}
if (
  hosted &&
  (process.env.NEXT_PUBLIC_E2E_TEST === "1" ||
    process.env.GRIDWATCH_LOCAL_DEMO === "1" ||
    process.env.NEXT_PUBLIC_DEMO_INSTANCE === "true" ||
    process.env.GRIDWATCH_TEST_BUILD === "1" ||
    process.env.GRIDWATCH_LOCAL_WEBSITE === "1")
) {
  throw new Error("Do not deploy demo, browser-test or local website builds");
}
if (hosted) {
  const commit =
    process.env.RELEASE_REVISION ||
    (netlify ? process.env.COMMIT_REF : process.env.VERCEL_GIT_COMMIT_SHA) ||
    "";
  if (
    !/^[0-9a-f]{40}$/.test(commit) ||
    (process.env.RELEASE_REVISION &&
      (netlify ? process.env.COMMIT_REF : process.env.VERCEL_GIT_COMMIT_SHA) &&
      process.env.RELEASE_REVISION !==
        (netlify ? process.env.COMMIT_REF : process.env.VERCEL_GIT_COMMIT_SHA))
  ) {
    throw new Error("Hosted release requires one matching full source commit");
  }
}
const config: NextConfig = {
  poweredByHeader: false,
  reactStrictMode: true,
  devIndicators: false,
  distDir:
    process.env.GRIDWATCH_TEST_BUILD === "1"
      ? ".next-test"
      : process.env.GRIDWATCH_LOCAL_DEMO === "1"
        ? ".next-demo"
        : process.env.GRIDWATCH_LOCAL_WEBSITE === "1"
          ? ".next-website"
          : ".next",
  turbopack: { root: path.resolve(process.cwd()) },
  async rewrites() {
    return [{ source: "/api/:path*", destination: `${url.origin}/api/:path*` }];
  },
  async headers() {
    return [
      {
        source: "/:path*",
        headers: [
          ...(hosted
            ? [{ key: "Strict-Transport-Security", value: "max-age=31536000" }]
            : []),
          { key: "X-Content-Type-Options", value: "nosniff" },
          { key: "Referrer-Policy", value: "strict-origin-when-cross-origin" },
          { key: "X-Frame-Options", value: "DENY" },
          {
            key: "Permissions-Policy",
            value: "camera=(), microphone=(), geolocation=()",
          },
          {
            key: "Content-Security-Policy",
            value: "frame-ancestors 'none'; object-src 'none'; base-uri 'self'",
          },
        ],
      },
      {
        source: "/api/:path*",
        headers: [{ key: "Cache-Control", value: "no-store" }],
      },
    ];
  },
};
export default config;
