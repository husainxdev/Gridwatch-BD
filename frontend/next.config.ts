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
        source: "/api/:path*",
        headers: [{ key: "Cache-Control", value: "no-store" }],
      },
    ];
  },
};
export default config;
