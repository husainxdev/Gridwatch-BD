import { defineConfig } from "@playwright/test";
export default defineConfig({
  testDir: "./e2e",
  workers: 1,
  reporter: "list",
  use: {
    baseURL: "http://localhost:15173",
    launchOptions: {
      executablePath: process.env.CHROMIUM_EXECUTABLE || undefined,
    },
    // Never record tokens, passwords or mail content in traces/screenshots.
    trace: "off",
    screenshot: "off",
    video: "off",
  },
});
