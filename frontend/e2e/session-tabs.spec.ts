import { test, expect } from "@playwright/test";
test("two tabs coordinate refresh and logout without persisting tokens", async ({
  page,
  context,
}) => {
  await page.goto("/register");
  await page.locator("input[name=name]").fill("Two tab tester");
  await page
    .locator("input[name=email]")
    .fill(`tabs-${crypto.randomUUID()}@example.com`);
  await page.locator("input[name=password]").fill("test-user-password");
  await page.getByRole("button", { name: "অ্যাকাউন্ট খুলুন" }).click();
  await expect(
    page.getByRole("heading", { name: "স্বাগতম, Two tab tester" }),
  ).toBeVisible();
  const other = await context.newPage();
  await other.goto("/dashboard");
  await expect(
    other.getByRole("heading", { name: "স্বাগতম, Two tab tester" }),
  ).toBeVisible();
  let refreshes = 0;
  for (const tab of [page, other]) {
    tab.on("request", (r) => {
      if (r.url().endsWith("/api/auth/refresh") && r.method() === "POST")
        refreshes++;
    });
    let first = true;
    await tab.route("**/api/auth/me", async (route) => {
      if (first) {
        first = false;
        await route.fulfill({
          status: 401,
          contentType: "application/json",
          body: JSON.stringify({ detail: "Controlled expired access test" }),
        });
      } else await route.continue();
    });
  }
  const values = await Promise.all(
    [page, other].map((tab) =>
      tab.evaluate(async () => {
        const { api } = window.__gridwatchTest!;
        return api("/api/auth/me");
      }),
    ),
  );
  expect(values[0].id).toBe(values[1].id);
  expect(refreshes).toBe(1);
  for (const tab of [page, other])
    expect(
      await tab.evaluate(() => ({
        local: localStorage.length,
        session: sessionStorage.length,
      })),
    ).toEqual({ local: 0, session: 0 });
  const area = await page.evaluate(async () => {
    const { api } = window.__gridwatchTest!;
    const area = (
      await api("/api/locations?search=Browser%20alternate%20district")
    ).items[0].id;
    await api("/api/activities", {
      method: "POST",
      body: JSON.stringify({
        title: "Private old-account activity",
        location_id: area,
        starts_at: new Date(Date.now() + 3600000).toISOString(),
        ends_at: new Date(Date.now() + 7200000).toISOString(),
      }),
    });
    return area;
  });
  await other.goto(`/activities?location_id=${area}`);
  await expect(
    other.getByText("Private old-account activity", { exact: true }),
  ).toBeVisible();
  // Auth pages redirect signed-in users. Exercise a replacement cookie session
  // through the real auth API to verify the other tab clears private state.
  await page.evaluate(async () => {
    const { api, acceptSession, withSessionLock } = window.__gridwatchTest!;
    await withSessionLock(async () => {
      acceptSession(
        await api(
          "/api/auth/register",
          {
            method: "POST",
            body: JSON.stringify({
              display_name: "New tab account",
              email: `tabs-new-${crypto.randomUUID()}@example.com`,
              password: "test-user-password",
            }),
          },
          false,
        ),
      );
    });
  });
  await expect(
    page.getByRole("heading", { name: "স্বাগতম, New tab account" }),
  ).toBeVisible();
  await expect(
    other.getByText("Private old-account activity", { exact: true }),
  ).toHaveCount(0);
  await expect(
    other.getByText("সংরক্ষিত কাজ নেই।", { exact: true }),
  ).toBeVisible();
  await page.getByRole("button", { name: "লগআউট", exact: true }).click();
  await expect(other).toHaveURL(/\/login$/);
  await expect(
    other.getByRole("heading", { name: "অ্যাকাউন্টে প্রবেশ" }),
  ).toBeVisible();
  await other.close();
});
