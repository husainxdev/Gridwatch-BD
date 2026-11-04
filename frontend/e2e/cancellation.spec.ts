import { test, expect } from "@playwright/test";

test("leaving pages cancels pending fetches without unhandled rejections", async ({
  page,
  request,
}) => {
  const failures: string[] = [];
  const pending: string[] = [];
  const aborted: string[] = [];
  page.on("pageerror", (error) => failures.push(error.message));
  page.on("requestfailed", (request) => {
    if (request.url().includes("/api/"))
      aborted.push(new URL(request.url()).pathname);
  });
  await page.addInitScript(() => {
    (
      window as typeof window & { unhandledRequests: string[] }
    ).unhandledRequests = [];
    window.addEventListener("unhandledrejection", (event) => {
      (
        window as typeof window & { unhandledRequests: string[] }
      ).unhandledRequests.push(String(event.reason));
    });
  });
  const selected = (
    await (
      await request.get(
        "/api/locations?kind=district&status=verified&page_size=1",
      )
    ).json()
  ).items[0].id;
  let release!: () => void;
  const gate = new Promise<void>((resolve) => {
    release = resolve;
  });
  await page.route("**/api/**", async (route) => {
    const path = new URL(route.request().url()).pathname;
    if (path === "/api/auth/refresh") {
      await route.fulfill({ status: 401, json: { detail: "No session" } });
      return;
    }
    pending.push(path);
    await gate;
    await route
      .fulfill({
        json: {
          data_mode: "demonstration",
          items: [],
          total: 0,
          page: 1,
          page_size: 20,
        },
      })
      .catch(() => {});
  });
  try {
    await page.goto(`/?location_id=${selected}`);
    await expect(page.locator("main h1")).toBeVisible();
    await expect.poll(() => pending.includes("/api/area-overview")).toBe(true);
    const nav = page.getByRole("navigation", { name: "প্রধান নেভিগেশন" });
    await nav.getByRole("link", { name: "নোটিশ", exact: true }).click();
    await expect
      .poll(
        () =>
          pending.includes("/api/notices") &&
          pending.includes("/api/schedules"),
      )
      .toBe(true);
    await nav
      .getByRole("link", { name: "উৎস ও তথ্যনীতি", exact: true })
      .click();
    await expect(page).toHaveURL(/\/sources$/);
    release();
    for (const path of ["/api/area-overview", "/api/notices", "/api/schedules"])
      await expect.poll(() => aborted.includes(path)).toBe(true);
    expect(
      await page.evaluate(
        () =>
          (window as typeof window & { unhandledRequests: string[] })
            .unhandledRequests,
      ),
    ).toEqual([]);
    expect(failures).toEqual([]);
    await expect(page.locator("main").getByRole("alert")).toHaveCount(0);
  } finally {
    release();
  }
});
