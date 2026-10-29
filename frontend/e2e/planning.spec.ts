import { test, expect } from "@playwright/test";
for (const width of [1440, 390]) {
  test(`admin planning and private history journey at ${width}px`, async ({
    browser,
  }) => {
    const adminContext = await browser.newContext({
      viewport: { width, height: 1000 },
    });
    const userContext = await browser.newContext({
      viewport: { width, height: 1000 },
    });
    const admin = await adminContext.newPage(),
      user = await userContext.newPage();
    admin.on("dialog", (d) =>
      d.accept(
        d.type() === "prompt" ? "Fictional notice cancelled by source" : "",
      ),
    );
    try {
      await admin.goto("/login");
      await admin.locator("input[name=email]").fill("phase-admin@example.com");
      await admin
        .locator("input[name=password]")
        .fill(process.env.BROWSER_TEST_PASSWORD!);
      await admin
        .getByRole("button", { name: "প্রবেশ করুন", exact: true })
        .click();
      await expect(
        admin.getByRole("heading", { name: "স্বাগতম, Phase test admin" }),
      ).toBeVisible();
      const fixture = await admin.evaluate(async () => {
        const { api } = window.__gridwatchTest!;
        const loc = (
          await api("/api/locations?search=Browser%20alternate%20district")
        ).items[0];
        const title = "Planning browser " + crypto.randomUUID();
        const n = await api("/api/admin/notices", {
          method: "POST",
          body: JSON.stringify({
            title,
            body: "Fictional testing announcement only",
            publisher: "Fictional office",
            source_url: "https://example.com/planning.pdf",
            published_at: null,
          }),
        });
        await api(`/api/admin/notices/${n.id}/verify`, {
          method: "POST",
          body: JSON.stringify({ version: 1 }),
        });
        return { area: loc.id, title, notice: n.id };
      });
      await admin.goto(
        `/admin?tab=notices&search=${encodeURIComponent(fixture.title)}`,
      );
      await admin.getByRole("button", { name: "প্রকাশ", exact: true }).click();
      await expect(admin.getByText("published · সংস্করণ 3")).toBeVisible();
      const schedule = await admin.evaluate(async ({ area, notice }) => {
        const { api, localInputTime } = window.__gridwatchTest!;
        const start = new Date(Date.now() + 86400000);
        start.setSeconds(0, 0);
        const end = new Date(start.getTime() + 7200000);
        const s = await api("/api/admin/schedules", {
          method: "POST",
          body: JSON.stringify({
            notice_id: notice,
            location_id: area,
            starts_at: start.toISOString(),
            ends_at: end.toISOString(),
          }),
        });
        return {
          id: s.id,
          start: localInputTime(start),
          end: localInputTime(end),
        };
      }, fixture);
      await admin.goto(`/admin?tab=schedules&search=${schedule.id}`);
      await admin.getByRole("button", { name: "প্রকাশ", exact: true }).click();
      await expect(admin.getByText("published · সংস্করণ 2")).toBeVisible();
      // Debounced filter and browser navigation restore URL state.
      await admin
        .getByLabel("খুঁজুন", { exact: true })
        .fill("no-such-schedule");
      await expect(admin).toHaveURL(/search=no-such-schedule/);
      await expect(
        admin.getByText("এই ফিল্টারে কোনো রেকর্ড নেই।"),
      ).toBeVisible();
      await admin.goBack();
      await expect(admin.getByLabel("খুঁজুন", { exact: true })).toHaveValue(
        schedule.id,
      );
      await expect(admin.getByText("published · সংস্করণ 2")).toBeVisible();
      await user.goto("/register");
      await user.locator("input[name=name]").fill("Planning user");
      await user
        .locator("input[name=email]")
        .fill(`planning-${crypto.randomUUID()}@example.com`);
      await user.locator("input[name=password]").fill("test-user-password");
      await user.getByRole("button", { name: "অ্যাকাউন্ট খুলুন" }).click();
      await expect(
        user.getByRole("heading", { name: "স্বাগতম, Planning user" }),
      ).toBeVisible();
      await user.goto(`/activities?location_id=${fixture.area}`);
      await user
        .getByLabel("কাজের নাম", { exact: true })
        .fill("Online Exam <safe text>");
      await user
        .getByLabel("শুরু · বাংলাদেশ", { exact: true })
        .fill(schedule.start);
      await user
        .getByLabel("শেষ · বাংলাদেশ", { exact: true })
        .fill(schedule.end);
      await user
        .getByRole("button", { name: "সংরক্ষণ ও মিলিয়ে দেখুন", exact: true })
        .click();
      await expect(
        user.getByRole("heading", {
          name: "আপনার কাজ ঘোষিত বিদ্যুৎ-বিরতির সময়ের সঙ্গে মিলেছে",
        }),
      ).toBeVisible();
      await expect(
        user.getByText("Online Exam <safe text>", { exact: true }),
      ).toBeVisible();
      await admin
        .getByRole("button", { name: "বাতিল চিহ্নিত", exact: true })
        .click();
      await expect(admin.getByText("published · সংস্করণ 3")).toBeVisible();
      await user
        .getByRole("button", { name: "খুলুন ও নতুন করে পরীক্ষা", exact: true })
        .click();
      await expect(
        user.getByRole("heading", {
          name: "মিলে যায় এমন প্রকাশিত বিদ্যুৎ-বিরতির ঘোষণা পাওয়া যায়নি",
        }),
      ).toBeVisible();
      const reported = await user.evaluate(async (area) => {
        const { api } = window.__gridwatchTest!;
        const start = new Date(Date.now() - 3600000);
        for (const [kind, offset] of [
          ["power_off", 0],
          ["power_back", 30],
        ] as const) {
          await api("/api/reports", {
            method: "POST",
            body: JSON.stringify({
              location_id: area,
              kind,
              observed_at: new Date(
                start.getTime() + offset * 60000,
              ).toISOString(),
              idempotency_key: crypto.randomUUID(),
            }),
          });
        }
        return start.toISOString();
      }, fixture.area);
      await user.goto(`/history?location_id=${fixture.area}`);
      await expect(
        user.getByRole("heading", { name: "আমার রেকর্ড করা বিভ্রাটের ইতিহাস" }),
      ).toBeVisible();
      await expect(
        user.locator(".record strong").filter({ hasText: /^সম্পূর্ণ$/ }),
      ).toBeVisible();
      await expect(user.getByText(/Duration: ৩০ মিনিট/)).toBeVisible();
      const summary = await user.evaluate(
        async ({ area, start }) => {
          const { api } = window.__gridwatchTest!;
          const q = new URLSearchParams({
            location_id: area,
            start,
            end: new Date().toISOString(),
          });
          return (await api(`/api/history?${q}`)).summary;
        },
        { area: fixture.area, start: reported },
      );
      expect(summary.recorded_episodes).toBe(1);
      expect(summary.known_minutes).toBe(30);
      expect(
        await user.evaluate(
          () => document.documentElement.scrollWidth <= innerWidth,
        ),
      ).toBe(true);
      await user.screenshot({
        path: `/tmp/gridwatch-history-${width}.png`,
        fullPage: true,
      });
      const reportId = await user.evaluate(async () => {
        const { api } = window.__gridwatchTest!;
        return (await api("/api/me/reports")).items[0].id;
      });
      await admin.goto(`/admin?tab=reports&search=${reportId}`);
      await admin.getByLabel("পর্যালোচনার সিদ্ধান্ত").selectOption("pending");
      await admin
        .getByLabel("কারণ", { exact: true })
        .fill("Restoration needs further review");
      await admin
        .getByRole("button", { name: "পর্যালোচনা সংরক্ষণ", exact: true })
        .click();
      await expect(
        admin.getByText("পর্যালোচনা সংরক্ষিত", { exact: true }),
      ).toBeVisible();
      await user.reload();
      await expect(
        user.getByText("খোলা · ফেরার তথ্য নেই", { exact: true }),
      ).toBeVisible();
      await admin.goto("/admin?tab=overview");
      await expect(
        admin.getByRole("heading", { name: "কাজের সারাংশ" }),
      ).toBeVisible();
      expect(
        await admin.evaluate(
          () => document.documentElement.scrollWidth <= innerWidth,
        ),
      ).toBe(true);
      await expect(
        admin.locator(".overview-grid strong").filter({ hasText: /^\d+$/ }),
      ).toHaveCount(4);
      await admin.screenshot({
        path: `/tmp/gridwatch-admin-${width}.png`,
        fullPage: true,
      });
    } finally {
      await userContext.close();
      await adminContext.close();
    }
  });
}
