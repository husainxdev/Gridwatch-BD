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
test("disabled demo data is an intentional empty state rather than a backend failure", async ({
  page,
}) => {
  await page.route("**/api/demo/areas", (route) =>
    route.fulfill({ status: 404, json: { detail: "Not found" } }),
  );
  await page.goto("/");
  await expect(
    page.getByRole("heading", { name: "নমুনা তথ্য এখানে দেখানো হচ্ছে না" }),
  ).toBeVisible();
  await expect(page.locator("main").getByRole("alert")).toHaveCount(0);
});
