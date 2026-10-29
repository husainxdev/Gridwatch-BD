import { test, expect } from "@playwright/test";
test("admin reviews sourced office and feeder mapping, then suspends it", async ({
  page,
}) => {
  await page.setViewportSize({ width: 390, height: 1000 });
  page.on("dialog", (d) =>
    d.accept(
      d.type() === "prompt"
        ? "Fictional source reviewed in automated test"
        : "",
    ),
  );
  await page.goto("/login");
  await page.locator("input[name=email]").fill("phase-admin@example.com");
  await page
    .locator("input[name=password]")
    .fill(process.env.BROWSER_TEST_PASSWORD!);
  await page.getByRole("button", { name: "প্রবেশ করুন", exact: true }).click();
  await expect(
    page.getByRole("heading", { name: "স্বাগতম, Phase test admin" }),
  ).toBeVisible();
  const title = "Fictional office " + Date.now();
  await page.goto("/admin?tab=offices");
  await page.getByLabel("বাংলা নাম", { exact: true }).fill(title);
  await page.getByLabel("English name", { exact: true }).fill(title);
  await page
    .getByLabel("মূল প্রমাণের HTTPS লিংক")
    .fill("https://example.com/test-office");
  await page
    .getByRole("button", { name: "খসড়া সংরক্ষণ", exact: true })
    .click();
  await expect(
    page.getByText("যাচাই-বাকি রেকর্ড সংরক্ষিত", { exact: true }),
  ).toBeVisible();
  await page
    .getByRole("button", { name: "উৎস দেখে যাচাই", exact: true })
    .click();
  await expect(
    page.getByText("verified · সক্রিয় · সংস্করণ 2", { exact: true }),
  ).toBeVisible();
  await page.goto("/admin?tab=mappings");
  await page.getByLabel("অফিস", { exact: true }).selectOption({ label: title });
  await page
    .getByLabel("উৎসে লেখা feeder নাম")
    .fill("Fictional feeder for browser test");
  await page.getByLabel("এলাকার নাম বা ID খুঁজুন").fill("Alternate area alias");
  await page
    .getByRole("button", {
      name: /পরীক্ষামূলক বিভাগ \/ দ্বিতীয় পরীক্ষামূলক জেলা/,
    })
    .click();
  await page
    .getByLabel("উৎসে লেখা নির্দিষ্ট আওতা ও সীমাবদ্ধতা")
    .fill("Fictional source explicitly describes the selected coverage only.");
  await page
    .getByLabel("মূল প্রমাণের HTTPS লিংক")
    .fill("https://example.com/test-coverage");
  await page
    .getByRole("button", { name: "খসড়া সংরক্ষণ", exact: true })
    .click();
  await expect(
    page.getByText("Fictional feeder for browser test", { exact: true }),
  ).toBeVisible();
  await page
    .getByRole("button", { name: "উৎস দেখে যাচাই", exact: true })
    .click();
  await expect(
    page.getByText("অফিস, এলাকা ও mapping-এর বর্তমান source review মেলে", {
      exact: true,
    }),
  ).toBeVisible();
  await page.getByRole("button", { name: "স্থগিত", exact: true }).click();
  await expect(
    page.getByText("unverified · স্থগিত · সংস্করণ 3", { exact: true }),
  ).toBeVisible();
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= innerWidth,
    ),
  ).toBe(true);
});
