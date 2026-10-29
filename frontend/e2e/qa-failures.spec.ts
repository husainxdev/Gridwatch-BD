import { test, expect } from "@playwright/test";

test("failed notices are not empty facts and retry preserves search", async ({
  page,
}) => {
  let fail = true;
  await page.route("**/api/notices?**", (r) =>
    fail
      ? r.fulfill({
          status: 503,
          json: { detail: "Controlled backend unavailable" },
        })
      : r.continue(),
  );
  await page.route("**/api/schedules?**", (r) =>
    fail
      ? r.fulfill({
          status: 503,
          json: { detail: "Controlled backend unavailable" },
        })
      : r.continue(),
  );
  await page.goto("/notices");
  await expect(page.locator("main").getByRole("alert")).toHaveCount(2);
  await expect(
    page.getByRole("heading", { name: "এখনো কোনো নোটিশ নেই" }),
  ).toHaveCount(0);
  await expect(
    page.getByText(
      "কোনো প্রকাশিত সময়সূচি পাওয়া যায়নি; বিদ্যুৎ থাকার নিশ্চয়তা নয়।",
    ),
  ).toHaveCount(0);
  await page.getByLabel("শিরোনাম খুঁজুন").fill("qa-no-matching-notice");
  await page.getByRole("button", { name: "খুঁজুন", exact: true }).click();
  fail = false;
  await page.getByRole("button", { name: "নোটিশ আবার লোড করুন" }).click();
  await page.getByRole("button", { name: "সময়সূচি আবার লোড করুন" }).click();
  await expect(
    page.getByRole("heading", { name: "এখনো কোনো নোটিশ নেই" }),
  ).toBeVisible();
  await expect(page.getByLabel("শিরোনাম খুঁজুন")).toHaveValue(
    "qa-no-matching-notice",
  );
  await expect(page.locator("main").getByRole("alert")).toHaveCount(0);
});

test("two users retain independent histories across a lost response and retry", async ({
  browser,
  request,
}) => {
  const auth = await request.post("/api/auth/login", {
    data: {
      email: "phase-admin@example.com",
      password: process.env.BROWSER_TEST_PASSWORD,
    },
  });
  const headers = {
    Authorization: `Bearer ${(await auth.json()).access_token}`,
  };
  const root = (
    await (await request.get("/api/locations?roots_only=true")).json()
  ).items[0].id;
  const alias = `qa-journey-${crypto.randomUUID()}`;
  const areaName = `Fictional QA journey district ${alias}`;
  const created = await request.post("/api/admin/locations", {
    headers,
    data: {
      name_bn: "কাল্পনিক QA জেলা " + alias,
      name_en: areaName,
      kind: "district",
      parent_id: root,
      slug: alias,
      aliases: [alias],
    },
  });
  expect(created.status()).toBe(201);
  const area = (await created.json()).id;
  expect(
    (
      await request.post(`/api/admin/locations/${area}/verify`, {
        headers,
        data: {
          version: 1,
          source_url: "https://example.com/fictional-qa-area",
        },
      })
    ).status(),
  ).toBe(200);
  const contexts = await Promise.all([
    browser.newContext(),
    browser.newContext(),
  ]);
  const [a, b] = await Promise.all(contexts.map((c) => c.newPage()));
  try {
    for (const [i, tab] of [a, b].entries()) {
      await tab.goto("/register");
      await tab.locator("input[name=name]").fill(`Fictional QA user ${i}`);
      await tab
        .getByLabel("ইমেইল", { exact: true })
        .fill(`qa-two-${i}-${crypto.randomUUID()}@example.com`);
      await tab
        .getByLabel("পাসওয়ার্ড", { exact: true })
        .fill("qa-user-password");
      await tab.getByRole("button", { name: "অ্যাকাউন্ট খুলুন" }).click();
      await expect(
        tab.getByRole("heading", { name: `স্বাগতম, Fictional QA user ${i}` }),
      ).toBeVisible();
      await tab.getByLabel("এলাকার নাম বা ID খুঁজুন").fill(alias);
      await tab.getByRole("button").filter({ hasText: areaName }).click();
      await expect(
        tab.getByRole("button", { name: "বিদ্যুৎ নেই", exact: true }),
      ).toBeEnabled();
    }
    const payloads: unknown[] = [];
    let first = true;
    await a.route("**/api/reports", async (route) => {
      payloads.push(route.request().postDataJSON());
      if (first) {
        first = false;
        await route.fetch();
        await route.abort("failed");
      } else await route.continue();
    });
    await a
      .getByLabel("ব্যক্তিগত মন্তব্য (ঐচ্ছিক)")
      .fill("QA preserved note <script>literal</script>");
    await a
      .getByRole("button", { name: "বিদ্যুৎ নেই", exact: true })
      .evaluate((button: HTMLButtonElement) => {
        button.click();
        button.click();
      });
    await expect(a.locator("main").getByRole("alert")).toBeVisible();
    expect(payloads).toHaveLength(1);
    await expect(
      a.getByText("আপনার সংযোগের রিপোর্ট জমা হয়েছে", { exact: true }),
    ).toHaveCount(0);
    await expect(a.getByLabel("ব্যক্তিগত মন্তব্য (ঐচ্ছিক)")).toHaveValue(
      "QA preserved note <script>literal</script>",
    );
    await a.getByRole("button", { name: "বিদ্যুৎ নেই", exact: true }).click();
    await expect(
      a.getByText("আপনার সংযোগের রিপোর্ট জমা হয়েছে", { exact: true }),
    ).toBeVisible();
    expect(payloads).toHaveLength(2);
    expect(payloads[1]).toEqual(payloads[0]);
    for (const [tab, button] of [
      [b, "বিদ্যুৎ নেই"],
      [b, "বিদ্যুৎ ফিরেছে"],
      [a, "আমার এখনো আসেনি"],
      [a, "বিদ্যুৎ ফিরেছে"],
    ] as const) {
      const submitted = tab.waitForResponse(
        (r) =>
          r.url().endsWith("/api/reports") && r.request().method() === "POST",
      );
      await tab.getByRole("button", { name: button, exact: true }).click();
      expect((await submitted).status()).toBe(201);
      await expect(
        tab.getByRole("button", { name: button, exact: true }),
      ).toBeEnabled();
    }
    for (const tab of [a, b]) {
      const episodes = await tab.evaluate(
        async () =>
          (
            await window.__gridwatchTest!.api<{
              items: { is_open: boolean }[];
            }>("/api/me/episodes")
          ).items,
      );
      expect(episodes).toHaveLength(1);
      expect(episodes[0].is_open).toBe(false);
    }
    const counts = await a.evaluate(async (area) => {
      return (
        await window.__gridwatchTest!.api<{
          counts: { power_off: number; power_back: number; still_off: number };
        }>(`/api/reports/summary?location_id=${area}`)
      ).counts;
    }, area);
    expect(counts.power_off).toBe(0);
    expect(counts.still_off).toBe(0);
    expect(counts.power_back).toBeGreaterThanOrEqual(2);
  } finally {
    for (const context of contexts) await context.close();
  }
});
