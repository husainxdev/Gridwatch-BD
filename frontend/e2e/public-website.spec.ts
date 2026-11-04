import { test, expect } from "@playwright/test";
import AxeBuilder from "@axe-core/playwright";

test("normal website has no demo branding and mobile menu is keyboard usable", async ({
  page,
}) => {
  const failures: string[] = [];
  page.on("pageerror", (error) => failures.push(error.message));
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto("/");
  await expect(page.locator("main h1")).toBeVisible();
  await expect(page.locator(".demo-banner")).toHaveCount(0);
  await expect(page.locator("body")).not.toContainText(
    "বিশ্ববিদ্যালয় প্রকল্প",
  );
  await expect(page.locator("body")).not.toContainText("প্রদর্শনী সংস্করণ");
  await expect(page.locator("body")).not.toContainText("PILOT ·");
  const primary = page.getByRole("navigation", { name: "প্রধান নেভিগেশন" });
  const help = primary.getByRole("link", { name: "ব্যবহার নির্দেশনা" });
  await expect(help).not.toBeVisible();
  const menu = page.getByRole("button", { name: "মেনু খুলুন", exact: true });
  await menu.focus();
  await page.keyboard.press("Enter");
  await expect(
    page.getByRole("button", { name: "মেনু বন্ধ করুন" }),
  ).toHaveAttribute("aria-expanded", "true");
  await expect(help).toBeVisible();
  await help.click();
  await expect(
    page.getByRole("heading", { name: "শুরু করুন তিনটি সহজ ধাপে" }),
  ).toBeVisible();
  await expect(
    page.getByRole("button", { name: "মেনু খুলুন" }),
  ).toHaveAttribute("aria-expanded", "false");
  const question = page.locator("summary").filter({ hasText: "সময়সূচি শেষ" });
  await question.focus();
  await page.keyboard.press("Enter");
  await expect(question.locator("..")).toHaveAttribute("open", "");
  await expect(question.locator("..")).toContainText(
    "বিদ্যুৎ ফেরার নিশ্চয়তা নয়",
  );
  for (const path of ["/help", "/privacy"]) {
    for (const width of [360, 390, 768, 1440]) {
      await page.setViewportSize({ width, height: 900 });
      await page.goto(path);
      await expect(page.locator("main h1")).toBeVisible();
      expect(
        await page.evaluate(
          () => document.documentElement.scrollWidth <= innerWidth,
        ),
      ).toBe(true);
      const results = await new AxeBuilder({ page })
        .withTags(["wcag2a", "wcag2aa", "wcag21aa", "wcag22aa"])
        .analyze();
      expect(
        results.violations.map((v) => ({
          id: v.id,
          targets: v.nodes.map((n) => n.target),
        })),
      ).toEqual([]);
    }
  }
  await page.goto("/register");
  const password = page.getByLabel("পাসওয়ার্ড", { exact: true });
  await password.fill("not-a-real-account-password");
  await expect(password).toHaveAttribute("type", "password");
  await page
    .getByRole("button", { name: "পাসওয়ার্ড দেখুন", exact: true })
    .click();
  await expect(password).toHaveAttribute("type", "text");
  await page
    .getByRole("button", { name: "পাসওয়ার্ড লুকান", exact: true })
    .click();
  await expect(password).toHaveAttribute("type", "password");
  expect(failures).toEqual([]);
});

test("area loading failure has an honest retry and successful empty state", async ({
  page,
}) => {
  let failed = true;
  await page.route("**/api/locations?roots_only=true**", (route) =>
    failed
      ? route.fulfill({
          status: 503,
          json: { detail: "Controlled location failure" },
        })
      : route.fulfill({
          json: { items: [], total: 0, page: 1, page_size: 100 },
        }),
  );
  await page.goto("/");
  const picker = page.locator(".home-picker");
  await expect(picker.getByRole("alert")).toBeVisible();
  await expect(
    picker.getByText("এখনো কোনো এলাকা প্রকাশিত হয়নি।", { exact: false }),
  ).toHaveCount(0);
  failed = false;
  await picker.getByRole("button", { name: "এলাকা আবার লোড করুন" }).click();
  await expect(picker.getByRole("alert")).toHaveCount(0);
  await expect(
    picker.getByText("এখনো কোনো এলাকা প্রকাশিত হয়নি।", { exact: false }),
  ).toBeVisible();
  await expect(
    picker.getByRole("button", { name: "পরবর্তী", exact: true }),
  ).toHaveCount(0);
});
