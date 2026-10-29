import { test, expect } from "@playwright/test";
import AxeBuilder from "@axe-core/playwright";

for (const width of [360, 390, 768, 1440]) {
  test(`QA rendered accessibility and keyboard walkthrough ${width}px`, async ({
    page,
  }) => {
    test.setTimeout(180000);
    await page.setViewportSize({ width, height: 800 });
    const errors: string[] = [];
    page.on("pageerror", (e) => errors.push(e.message));
    async function inspect(path: string) {
      await page.goto(path);
      await expect(page.locator("main")).toBeVisible();
      await expect(page.locator("main .loading-state")).toHaveCount(0);
      const result = await new AxeBuilder({ page })
        .withTags(["wcag2a", "wcag2aa", "wcag21aa", "wcag22aa"])
        .analyze();
      expect(
        result.violations.map((v) => ({
          id: v.id,
          impact: v.impact,
          targets: v.nodes.map((n) => n.target),
        })),
      ).toEqual([]);
      expect(
        await page.evaluate(
          () => document.documentElement.scrollWidth <= innerWidth,
        ),
      ).toBe(true);
    }
    for (const path of [
      "/",
      "/sources",
      "/login",
      "/register",
      "/forgot",
      "/notices",
    ])
      await inspect(path);
    await page.goto("/login");
    await page
      .getByLabel("ইমেইল", { exact: true })
      .fill("phase-admin@example.com");
    await page
      .getByLabel("পাসওয়ার্ড", { exact: true })
      .fill(process.env.BROWSER_TEST_PASSWORD!);
    await page
      .getByRole("button", { name: "প্রবেশ করুন", exact: true })
      .click();
    await expect(
      page.getByRole("heading", { name: "স্বাগতম, Phase test admin" }),
    ).toBeVisible();
    for (const path of [
      "/dashboard",
      "/activities",
      "/history",
      "/admin?tab=overview",
      "/admin?tab=notices",
      "/admin?tab=reports",
      "/admin?tab=areas",
      "/admin?tab=offices",
      "/admin?tab=mappings",
      "/admin?tab=audit",
    ])
      await inspect(path);
    await page.goto("/dashboard");
    await expect(
      page.getByRole("heading", { name: "স্বাগতম, Phase test admin" }),
    ).toBeVisible();
    await page.keyboard.press("Tab");
    await expect(
      page.getByRole("link", { name: "মূল তথ্যে যান" }),
    ).toBeFocused();
    await page.keyboard.press("Enter");
    await expect(page.locator("#main")).toBeFocused();
    const search = page.getByLabel("এলাকার নাম বা ID খুঁজুন");
    await search.fill("Browser district alias");
    const choice = page
      .getByRole("button")
      .filter({ hasText: "Browser test district" });
    await expect(choice).toBeVisible();
    await page.keyboard.press("Tab");
    await expect(choice).toBeFocused();
    await page.keyboard.press("Enter");
    await expect(
      page.getByRole("button", { name: "বিদ্যুৎ নেই", exact: true }),
    ).toBeEnabled();
    const populated = await new AxeBuilder({ page })
      .withTags(["wcag2a", "wcag2aa", "wcag21aa", "wcag22aa"])
      .analyze();
    expect(
      populated.violations.map((v) => ({
        id: v.id,
        targets: v.nodes.map((n) => n.target),
      })),
    ).toEqual([]);
    await page.screenshot({
      path: `/tmp/gridwatch-qa-dashboard-${width}.png`,
      fullPage: true,
    });
    await page.setViewportSize({ width, height: 400 });
    await page.goto("/activities");
    const title = page.getByLabel("কাজের নাম", { exact: true });
    await title.fill("কাল্পনিক পরীক্ষা");
    await title.focus();
    await title.scrollIntoViewIfNeeded();
    const bounds = await title.boundingBox();
    expect(bounds!.y).toBeGreaterThanOrEqual(0);
    expect(bounds!.y + bounds!.height).toBeLessThanOrEqual(400);
    if (width < 640)
      expect(
        await title.evaluate((el) => parseFloat(getComputedStyle(el).fontSize)),
      ).toBeGreaterThanOrEqual(16);
    await page
      .getByRole("button", { name: "সংরক্ষণ ও মিলিয়ে দেখুন", exact: true })
      .scrollIntoViewIfNeeded();
    await expect(
      page.getByRole("button", {
        name: "সংরক্ষণ ও মিলিয়ে দেখুন",
        exact: true,
      }),
    ).toBeVisible();
    expect(errors).toEqual([]);
  });
}
