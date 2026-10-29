import { test, expect } from "@playwright/test";

test("Next routes support direct loads, client navigation and real 404 status", async ({
  page,
}) => {
  let refreshes = 0;
  page.on("request", (r) => {
    if (r.url().endsWith("/api/auth/refresh")) refreshes++;
  });
  const sessionRestore = page.waitForResponse(
    (r) =>
      r.url().endsWith("/api/auth/refresh") && r.request().method() === "POST",
  );
  const response = await page.goto("/sources");
  await sessionRestore;
  expect(response?.status()).toBe(200);
  await expect(page.locator("main h1")).toBeVisible();
  const initialRefreshes = refreshes;
  const marker = await page.evaluate(() => {
    const value = crypto.randomUUID();
    (
      window as typeof window & { nextNavigationMarker: string }
    ).nextNavigationMarker = value;
    return value;
  });
  await page
    .getByRole("navigation", { name: "প্রধান নেভিগেশন" })
    .getByRole("link", { name: "নোটিশ", exact: true })
    .click();
  await expect(page).toHaveURL(/\/notices$/);
  await expect(page.locator("main h1")).toBeVisible();
  expect(
    await page.evaluate(
      () =>
        (window as typeof window & { nextNavigationMarker: string })
          .nextNavigationMarker,
    ),
  ).toBe(marker);
  expect(refreshes).toBe(initialRefreshes);
  await page.goBack();
  await expect(page).toHaveURL(/\/sources$/);
  const missing = await page.goto("/a-page-that-does-not-exist");
  expect(missing?.status()).toBe(404);
  await expect(
    page.getByRole("heading", { name: "পাতাটি পাওয়া যায়নি" }),
  ).toBeVisible();
});
