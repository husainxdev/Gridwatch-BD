import { test, expect } from "@playwright/test";
import AxeBuilder from "@axe-core/playwright";

test("public home renders real area evidence, preserves stale facts and changes area safely", async ({
  page,
  request,
}) => {
  test.setTimeout(120000);
  const errors: string[] = [];
  page.on("pageerror", (e) => errors.push(e.message));
  const admin = await (
    await request.post("/api/auth/login", {
      data: {
        email: "phase-admin@example.com",
        password: process.env.BROWSER_TEST_PASSWORD!,
      },
    })
  ).json();
  const headers = { Authorization: "Bearer " + admin.access_token };
  const suffix = crypto.randomUUID();
  const locations: { id: string; name_bn: string }[] = [];
  for (const letter of ["A", "B"]) {
    const response = await request.post("/api/admin/locations", {
      headers,
      data: {
        name_bn: `কাল্পনিক public ${letter} ${suffix}`,
        name_en: `Fictional public ${letter} ${suffix}`,
        slug: `public-${letter.toLowerCase()}-${suffix}`,
        kind: "division",
        aliases: [`Public ${letter} ${suffix}`],
      },
    });
    expect(response.status()).toBe(201);
    const item = await response.json();
    expect(
      (
        await request.post(`/api/admin/locations/${item.id}/verify`, {
          headers,
          data: {
            version: 1,
            source_url: "https://example.com/fictional-public-location",
          },
        })
      ).status(),
    ).toBe(200);
    locations.push(item);
  }
  const area = locations[0].id;
  const title = `Fictional public notice ${suffix}`;
  const notice = await (
    await request.post("/api/admin/notices", {
      headers,
      data: {
        title,
        body: "Fictional QA announcement, not real electricity data",
        source_url: "https://example.com/fictional-public-notice",
        publisher: "Fictional public QA",
        published_at: null,
      },
    })
  ).json();
  expect(
    (
      await request.post(`/api/admin/notices/${notice.id}/verify`, {
        headers,
        data: { version: 1 },
      })
    ).status(),
  ).toBe(200);
  expect(
    (
      await request.post(`/api/admin/notices/${notice.id}/publish`, {
        headers,
        data: { version: 2 },
      })
    ).status(),
  ).toBe(200);
  const instant = Date.now();
  const schedule = await (
    await request.post("/api/admin/schedules", {
      headers,
      data: {
        notice_id: notice.id,
        location_id: area,
        starts_at: new Date(instant + 3600000).toISOString(),
        ends_at: new Date(instant + 7200000).toISOString(),
      },
    })
  ).json();
  expect(
    (
      await request.post(`/api/admin/schedules/${schedule.id}/publish`, {
        headers,
        data: { version: 1 },
      })
    ).status(),
  ).toBe(200);
  for (const [kind, minutes] of [
    ["still_off", 2],
    ["power_back", 1],
  ] as const) {
    const person = await (
      await request.post("/api/auth/register", {
        data: {
          email: `fictional-public-${crypto.randomUUID()}@example.com`,
          password: "public-test-only-password",
          display_name: "Fictional public reporter",
        },
      })
    ).json();
    expect(
      (
        await request.post("/api/reports", {
          headers: { Authorization: "Bearer " + person.access_token },
          data: {
            location_id: area,
            kind,
            observed_at: new Date(instant - minutes * 60000).toISOString(),
            idempotency_key: crypto.randomUUID(),
            note: "PRIVATE PUBLIC TEST NOTE",
          },
        })
      ).status(),
    ).toBe(201);
  }
  await page.goto(`/?location_id=${area}`);
  await expect(
    page.getByRole("heading", { name: locations[0].name_bn }),
  ).toBeVisible();
  await expect(page.getByText(title)).toBeVisible();
  await expect(page.locator(".home-counts dd")).toHaveText(["১", "১", "২"]);
  await expect(page.getByText("এলাকার বিদ্যুৎ অবস্থা: অজানা")).toBeVisible();
  await expect(page.getByText("PRIVATE PUBLIC TEST NOTE")).toHaveCount(0);
  // The same cleanup event is emitted when anonymous session restore gets 401.
  // Public evidence survives; separate account-switch tests enforce private clearing.
  await page.evaluate(() =>
    window.dispatchEvent(new Event("gridwatch-session-ended")),
  );
  await expect(page.locator(".home-counts dd")).toHaveText(["১", "১", "২"]);
  for (const width of [360, 390, 768, 1440]) {
    await page.setViewportSize({ width, height: 900 });
    const overflow = await page.evaluate(() =>
      Array.from(document.querySelectorAll("main *"))
        .filter((element) => {
          const r = element.getBoundingClientRect();
          return r.width > 0 && (r.right > innerWidth + 1 || r.left < -1);
        })
        .map((element) => ({
          tag: element.tagName,
          classes: element.className,
        })),
    );
    expect(overflow).toEqual([]);
    expect(
      await page.evaluate(
        () => document.documentElement.scrollWidth <= innerWidth,
      ),
    ).toBe(true);
    const result = await new AxeBuilder({ page })
      .withTags(["wcag2a", "wcag2aa", "wcag21aa", "wcag22aa"])
      .analyze();
    expect(
      result.violations.map((v) => ({
        id: v.id,
        targets: v.nodes.map((n) => n.target),
      })),
    ).toEqual([]);
  }
  const observed = await page
    .locator(".home-report-list li span")
    .first()
    .textContent();
  let fail = true;
  await page.route("**/api/area-overview?**", (route) =>
    fail
      ? route.fulfill({
          status: 503,
          json: { detail: "Controlled unavailable" },
        })
      : route.continue(),
  );
  await page.getByRole("button", { name: "হালনাগাদ করুন" }).click();
  await expect(page.locator("main").getByRole("alert")).toContainText(
    "আগের তথ্য পুরোনো",
  );
  await expect(page.locator(".home-counts dd")).toHaveText(["১", "১", "২"]);
  fail = false;
  await page
    .getByRole("button", { name: "আবার চেষ্টা করুন", exact: true })
    .click();
  await expect(page.locator("main").getByRole("alert")).toHaveCount(0);
  expect(
    await page.locator(".home-report-list li span").first().textContent(),
  ).toBe(observed);
  await page.getByLabel("এলাকার নাম বা ID খুঁজুন").fill(`Public B ${suffix}`);
  await page
    .getByRole("button")
    .filter({ hasText: locations[1].name_bn })
    .click();
  await expect(
    page.getByRole("heading", { name: locations[1].name_bn }),
  ).toBeVisible();
  await expect(page.locator(".home-counts dd")).toHaveText(["০", "০", "০"]);
  await expect(page.getByText(title)).toHaveCount(0);
  expect(errors).toEqual([]);
});

test("login/signup preserve the intended route and reject external or looping returns", async ({
  page,
}) => {
  await page.goto("/activities?search=return-check");
  await expect(
    page.getByRole("heading", { name: "অ্যাকাউন্টে প্রবেশ" }),
  ).toBeVisible();
  expect(new URL(page.url()).searchParams.get("next")).toBe(
    "/activities?search=return-check",
  );
  await page.getByRole("link", { name: "নিবন্ধন", exact: true }).click();
  await page.locator("input[name=name]").fill("Fictional return path user");
  await page
    .locator("input[name=email]")
    .fill(`return-${crypto.randomUUID()}@example.com`);
  await page.locator("input[name=password]").fill("return-test-only-password");
  await page.getByRole("button", { name: "অ্যাকাউন্ট খুলুন" }).click();
  await expect(page).toHaveURL(/\/activities\?search=return-check$/);
  await expect(page.getByLabel("কাজ খুঁজুন")).toHaveValue("return-check");
  for (const unsafe of [
    "https://escape.invalid/path",
    "//escape.invalid/path",
    "/\\escape.invalid",
    "/login",
    "/reset#token=never-use",
    "/dashboard\n",
  ]) {
    await page.goto(`/login?next=${encodeURIComponent(unsafe)}`);
    await expect(page).toHaveURL(/\/dashboard$/);
  }
  await page.goto(
    `/login?next=${encodeURIComponent("/history?status=completed")}`,
  );
  await expect(page).toHaveURL(/\/history\?status=completed$/);
  await expect(
    page.getByRole("heading", { name: "আমার রেকর্ড করা বিভ্রাটের ইতিহাস" }),
  ).toBeVisible();
});
