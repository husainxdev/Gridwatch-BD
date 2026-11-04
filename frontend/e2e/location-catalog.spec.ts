import { test, expect } from "@playwright/test";

test("source-reviewed Sylhet wards can be found, selected and saved through the real backend", async ({
  page,
}) => {
  test.setTimeout(90000);
  const errors: string[] = [];
  page.on("pageerror", (error) => errors.push(error.message));
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto("/");
  const picker = page.locator(".home-picker");
  await picker
    .getByRole("button", { name: "সিলেট সিটি কর্পোরেশন", exact: true })
    .click();
  await expect(
    picker.getByRole("region", { name: "ওয়ার্ড বাছুন" }),
  ).toBeVisible();
  await expect(picker.locator(".ward-grid button")).toHaveCount(42);
  await picker
    .locator(".ward-grid")
    .getByRole("button", { name: "১ নম্বর ওয়ার্ড", exact: true })
    .click();
  await expect(
    page
      .locator(".home-board")
      .getByRole("heading", { name: "১ নম্বর ওয়ার্ড", exact: true }),
  ).toBeVisible();
  await expect(picker.locator(".chosen-location")).toContainText("মূল উৎস");
  await expect(picker.locator(".chosen-location a")).toHaveAttribute(
    "href",
    "https://scc.gov.bd/pages/static-pages/6922dcfd933eb65569e1310d",
  );
  await expect(page.getByText("এলাকার বিদ্যুৎ অবস্থা: অজানা")).toBeVisible();
  await expect(page.locator(".home-counts dd")).toHaveText(["০", "০", "০"]);
  for (const term of [" Ward 1 ", "সিলেট ওয়ার্ড ১", "ওয়ার্ড ০১"]) {
    await picker.getByLabel("এলাকার নাম খুঁজুন").fill(term);
    await expect(
      picker.locator(".location-search-results li").first(),
    ).toContainText("১ নম্বর ওয়ার্ড");
    await picker.getByLabel("এলাকার নাম খুঁজুন").press("ArrowDown");
    await expect(
      picker.locator(".location-search-results button").first(),
    ).toBeFocused();
    await page.keyboard.press("Enter");
    await expect(picker.locator(".chosen-location")).toContainText(
      "১ নম্বর ওয়ার্ড",
    );
  }
  await page
    .getByRole("link", { name: "প্রবেশ করে রিপোর্ট দিন", exact: true })
    .click();
  await expect(
    page.getByRole("heading", { name: "অ্যাকাউন্টে প্রবেশ" }),
  ).toBeVisible();
  await page.getByRole("link", { name: "নিবন্ধন", exact: true }).click();
  await page
    .getByLabel("নাম", { exact: true })
    .fill("Fictional catalog journey user");
  await page
    .getByLabel("ইমেইল", { exact: true })
    .fill(`catalog-${crypto.randomUUID()}@example.com`);
  await page
    .getByLabel("পাসওয়ার্ড", { exact: true })
    .fill("isolated-browser-only-password");
  await page
    .getByRole("button", { name: "অ্যাকাউন্ট খুলুন", exact: true })
    .click();
  await expect(
    page.getByRole("heading", {
      name: "স্বাগতম, Fictional catalog journey user",
    }),
  ).toBeVisible();
  await expect(page.locator(".selected-area")).toContainText("১ নম্বর ওয়ার্ড");
  await page
    .getByRole("button", { name: "এলাকা সংরক্ষণ", exact: true })
    .click();
  await expect(
    page.getByRole("button", { name: "সরান", exact: true }),
  ).toBeVisible();
  await page.reload();
  await expect(page.locator(".selected-area")).toContainText("১ নম্বর ওয়ার্ড");
  const dashboardPicker = page.locator(".panel").filter({
    has: page.getByRole("heading", { name: "এলাকা নির্বাচন", exact: true }),
  });
  await dashboardPicker.getByLabel("এলাকার নাম খুঁজুন").fill("Ward 2");
  await expect(
    dashboardPicker.locator(".location-search-results li").first(),
  ).toContainText("২ নম্বর ওয়ার্ড");
  await dashboardPicker
    .locator(".location-search-results button")
    .first()
    .click();
  await expect(page.locator(".selected-area")).toContainText("২ নম্বর ওয়ার্ড");
  await page.goBack();
  await expect(page.locator(".selected-area")).toContainText("১ নম্বর ওয়ার্ড");
  await page.getByRole("button", { name: "লগআউট", exact: true }).click();
  await expect(
    page.getByRole("heading", { name: "অ্যাকাউন্টে প্রবেশ" }),
  ).toBeVisible();
  expect(errors).toEqual([]);
});

test("actual 42-ward selection grid stays usable and accessible at four widths", async ({
  page,
}) => {
  test.setTimeout(90000);
  const AxeBuilder = (await import("@axe-core/playwright")).default;
  for (const width of [360, 390, 768, 1440]) {
    await page.setViewportSize({ width, height: 900 });
    await page.goto("/");
    const picker = page.locator(".home-picker");
    await picker
      .getByRole("button", { name: "সিলেট সিটি কর্পোরেশন", exact: true })
      .click();
    await expect(picker.locator(".ward-grid button")).toHaveCount(42);
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
    const last = picker.locator(".ward-grid button").last();
    await last.focus();
    await page.keyboard.press("Enter");
    await expect(picker.locator(".chosen-location")).toContainText(
      "৪২ নম্বর ওয়ার্ড",
    );
  }
});
