import { test, expect } from "@playwright/test";
test("admin publication and personal outage restoration use real backend", async ({
  page,
}) => {
  page.on("dialog", (dialog) => dialog.accept());
  await page.goto("/login");
  await page.locator("input[name=email]").fill("phase-admin@example.com");
  await page
    .locator("input[name=password]")
    .fill(process.env.BROWSER_TEST_PASSWORD!);
  await page.getByRole("button", { name: "প্রবেশ করুন", exact: true }).click();
  await expect(
    page.getByRole("heading", { name: "স্বাগতম, Phase test admin" }),
  ).toBeVisible();
  const ids = await page.evaluate(async () => {
    const path = "/src/client.ts";
    const { api } = await import(path);
    const areas = await api("/api/locations?search=Browser%20test%20district");
    const n = await api("/api/admin/notices", {
      method: "POST",
      body: JSON.stringify({
        title: "Fictional browser notice",
        body: "Fictional automated integration notice only",
        publisher: "Fictional office",
        source_url: "https://example.com/browser.pdf",
        published_at: null,
      }),
    });
    await api(`/api/admin/notices/${n.id}/verify`, {
      method: "POST",
      body: JSON.stringify({ version: 1 }),
    });
    return { notice: n.id, area: areas.items[0].id };
  });
  await page.goto("/admin");
  await page.getByRole("button", { name: "নোটিশ", exact: true }).click();
  await page.getByRole("button", { name: "প্রকাশ", exact: true }).click();
  await expect(page.getByText("published · সংস্করণ 3")).toBeVisible();
  await page.evaluate(async ({ notice, area }) => {
    const path = "/src/client.ts";
    const { api } = await import(path);
    const start = new Date(Date.now() + 3600000).toISOString(),
      end = new Date(Date.now() + 7200000).toISOString();
    await api("/api/admin/schedules", {
      method: "POST",
      body: JSON.stringify({
        notice_id: notice,
        location_id: area,
        starts_at: start,
        ends_at: end,
      }),
    });
  }, ids);
  await page.getByRole("button", { name: "সময়সূচি", exact: true }).click();
  await page.getByRole("button", { name: "প্রকাশ", exact: true }).click();
  await expect(page.getByText("published · সংস্করণ 2")).toBeVisible();
  await page.getByRole("button", { name: "লগআউট", exact: true }).click();
  await page.goto("/register");
  await page.locator("input[name=name]").fill("Observation tester");
  await page
    .locator("input[name=email]")
    .fill(`observation-${Date.now()}@example.com`);
  await page.locator("input[name=password]").fill("test-user-password");
  await page.getByRole("button", { name: "অ্যাকাউন্ট খুলুন" }).click();
  await expect(
    page.getByRole("heading", { name: "স্বাগতম, Observation tester" }),
  ).toBeVisible();
  await page.goto("/notices");
  await expect(page.getByText("Fictional browser notice")).toBeVisible();
  await expect(
    page.getByRole("heading", { name: "ঘোষিত সময়সূচি" }),
  ).toBeVisible();
  await page.goto("/dashboard");
  await page
    .getByLabel("এলাকার নাম বা ID খুঁজুন")
    .fill("Browser district alias");
  await page
    .getByRole("button", { name: /পরীক্ষামূলক বিভাগ \/ পরীক্ষামূলক জেলা/ })
    .click();
  await page.getByRole("button", { name: "বিদ্যুৎ নেই", exact: true }).click();
  await expect(
    page.getByText("আপনার সংযোগের রিপোর্ট জমা হয়েছে"),
  ).toBeVisible();
  // Replaying exactly the same request returns the existing report.
  await page.evaluate(async () => {
    const path = "/src/client.ts";
    const { api } = await import(path);
    const r = (await api("/api/me/reports")).items[0];
    const replay = await api("/api/reports", {
      method: "POST",
      body: JSON.stringify({
        location_id: r.location_id,
        kind: r.kind,
        observed_at: r.observed_at,
        idempotency_key: r.idempotency_key,
        note: r.note,
      }),
    });
    if (replay.id !== r.id) throw Error("Retry created another observation");
  });
  await page
    .getByRole("button", { name: "বিদ্যুৎ ফিরেছে", exact: true })
    .click();
  await page.getByRole("button", { name: "রিপোর্ট ও ইতিহাস রিফ্রেশ" }).click();
  await expect(
    page.getByRole("heading", { name: "আমার সংযোগের বিভ্রাট ইতিহাস" }),
  ).toBeVisible();
  await expect
    .poll(() =>
      page.evaluate(async () => {
        const path = "/src/client.ts";
        const { api } = await import(path);
        const r = await api("/api/me/episodes");
        return r.items.length === 1 && !r.items[0].is_open;
      }),
    )
    .toBe(true);
});
