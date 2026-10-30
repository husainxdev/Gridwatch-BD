import type { NextConfig } from "next";
import path from "node:path";

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
  process.env.VERCEL === "1" &&
  (!process.env.GRIDWATCH_API_TARGET || url.protocol !== "https:")
) {
  throw new Error(
    "Vercel deployments require the explicit HTTPS backend origin",
  );
}
if (process.env.VERCEL === "1" && process.env.NEXT_PUBLIC_E2E_TEST === "1") {
  throw new Error("Do not deploy browser-test builds");
}
if (process.env.VERCEL === "1") {
  const commit =
    process.env.RELEASE_REVISION || process.env.VERCEL_GIT_COMMIT_SHA || "";
  if (
    !/^[0-9a-f]{40}$/.test(commit) ||
    (process.env.RELEASE_REVISION &&
      process.env.VERCEL_GIT_COMMIT_SHA &&
      process.env.RELEASE_REVISION !== process.env.VERCEL_GIT_COMMIT_SHA)
  ) {
    throw new Error("Vercel release requires one matching full source commit");
  }
}
const config: NextConfig = {
  poweredByHeader: false,
  reactStrictMode: true,
  devIndicators: false,
  distDir: process.env.GRIDWATCH_TEST_BUILD === "1" ? ".next-test" : ".next",
  turbopack: { root: path.resolve(process.cwd()) },
  async rewrites() {
    return [{ source: "/api/:path*", destination: `${url.origin}/api/:path*` }];
  },
  async headers() {
    return [
      {
        source: "/:path*",
        headers: [
          ...(process.env.VERCEL === "1"
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
