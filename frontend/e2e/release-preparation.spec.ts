import { test, expect } from "@playwright/test";
test("release identity and security headers accompany normal deep-link shells", async ({
  request,
}) => {
  const web = await request.get("/release-info");
  expect(web.status()).toBe(200);
  const metadata = await web.json();
  expect(metadata.service).toBe("gridwatch-web");
  expect(metadata.revision).toMatch(/^(unversioned|[a-f0-9]{40})$/);
  const api = await (await request.get("/api/health/live")).json();
  expect(api.instance_mode).toBe(metadata.instance_mode);
  for (const path of ["/dashboard", "/notices", "/reset"]) {
    const response = await request.get(path);
    expect(response.status()).toBe(200);
    expect(response.headers()["x-content-type-options"]).toBe("nosniff");
    expect(response.headers()["x-frame-options"]).toBe("DENY");
    expect(response.headers()["content-security-policy"]).toContain(
      "frame-ancestors 'none'",
    );
  }
});
test("public home uses real published notices and treats backend failure as an error", async ({
  page,
}) => {
  let failed = true;
  await page.route("**/api/notices?page_size=3", (route) =>
    failed
      ? route.fulfill({ status: 503, json: { detail: "Controlled failure" } })
      : route.continue(),
  );
  await page.goto("/");
  await expect(page.locator("main").getByRole("alert")).toContainText(
    "কোনো সংখ্যা ধরে নেওয়া হচ্ছে না",
  );
  await expect(
    page.getByRole("heading", { name: "প্রকাশিত নোটিশ যোগ হয়নি" }),
  ).toHaveCount(0);
  failed = false;
  await page
    .getByRole("button", { name: "আবার চেষ্টা করুন", exact: true })
    .click();
  await expect(page.locator("main").getByRole("alert")).toHaveCount(0);
  await expect(
    page.getByRole("link", { name: /সব প্রকাশিত নোটিশ দেখুন/ }),
  ).toBeVisible();
});
