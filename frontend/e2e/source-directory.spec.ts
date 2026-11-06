import { test, expect } from "@playwright/test";
import AxeBuilder from "@axe-core/playwright";

test("unified directory finds real source records without making historical report targets", async ({
  page,
  request,
}) => {
  test.setTimeout(120000);
  const errors: string[] = [];
  page.on("pageerror", (error) => errors.push(error.message));
  const summary = await (await request.get("/api/directory/summary")).json();
  expect(summary.counts).toEqual({ portal: 428, census2022: 5765 });
  await page.goto("/areas");
  await expect(
    page.getByRole("heading", { name: /আপনার এলাকা খুঁজে নিন/ }),
  ).toBeVisible();
  await expect(page.locator(".directory-results > li")).toHaveCount(4);
  const input = page.getByLabel("কোন এলাকা খুঁজছেন?");
  await input.fill("আম্বরখানা");
  // No Enter, submit, or source switch is required.
  await expect(page.locator(".directory-results")).toContainText("Ambarkhana");
  await expect(page.locator(".directory-results")).toContainText(
    "Airport Thana",
  );
  await expect(
    page.locator(".directory-results .explorer-power-link"),
  ).toHaveCount(0);
  await page.locator(".explorer-source summary").first().click();
  await expect(
    page.getByRole("link", { name: "জনশুমারির মূল PDF" }).first(),
  ).toHaveAttribute("href", /#page=164$/);
  await input.fill("Airport Ambarkhana");
  await expect(page.locator(".directory-results")).toContainText("Ambarkhana");
  await input.fill("বালাগঞ্জ");
  await expect(page.locator(".directory-results")).toContainText("বালাগঞ্জ");
  await expect(
    page.locator(".directory-results .explorer-power-link").first(),
  ).toBeVisible();
  await page.getByRole("button", { name: "উপ-এলাকা (৬)", exact: true }).click();
  await expect(page.locator(".directory-results > li")).toHaveCount(6);
  await expect(
    page.getByRole("navigation", { name: "তালিকার পূর্বসূরি" }),
  ).toContainText("বালাগঞ্জ");
  await page.goBack();
  await expect(input).toHaveValue("বালাগঞ্জ");
  await page.reload();
  await expect(input).toHaveValue("বালাগঞ্জ");
  await expect(
    page.locator(".directory-results .explorer-power-link").first(),
  ).toBeVisible();
  // Keyboard access: ArrowDown goes to a real result action; Escape clears.
  await input.focus();
  await input.press("ArrowDown");
  expect(
    await page
      .locator("#directory-results")
      .evaluate((node) => node.contains(document.activeElement)),
  ).toBe(true);
  await input.focus();
  await input.press("Escape");
  await expect(input).toHaveValue("");
  await expect(page.locator(".directory-results > li")).toHaveCount(4);
  await input.fill("no-such-place-xyzz");
  await expect(
    page.getByRole("heading", { name: "এই অনুসন্ধানে এলাকা পাওয়া যায়নি" }),
  ).toBeVisible();
  // Search from the actual homepage also shows village identities directly.
  await page.goto("/");
  await page.getByLabel("এলাকার নাম খুঁজুন").fill("আম্বরখানা");
  await expect(
    page.getByRole("region", { name: "গ্রাম ও মহল্লার পরিচয়" }),
  ).toContainText("Ambarkhana");
  await page.getByRole("link", { name: /সব তালিকায় খুঁজুন/ }).click();
  await expect(page.locator(".directory-results")).toContainText("Ambarkhana");
  expect(errors).toEqual([]);
});

test("directory is readable and keyboard accessible at four viewport widths", async ({
  page,
}) => {
  test.setTimeout(120000);
  for (const search of ["", "বালাগঞ্জ", "আম্বরখানা"]) {
    await page.goto("/areas?" + new URLSearchParams({ search }));
    await expect(page.locator(".directory-results > li").first()).toBeVisible();
    for (const width of [360, 390, 768, 1440]) {
      await page.setViewportSize({ width, height: 900 });
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
  }
});

test("old backend 404 is actionable, preserves the search, and recovers without false empty results", async ({
  page,
}) => {
  await page.route("**/api/directory?**", (route) =>
    route.fulfill({
      status: 404,
      contentType: "application/json",
      body: JSON.stringify({ detail: "Not Found" }),
    }),
  );
  await page.goto("/areas?search=আম্বরখানা");
  await expect(page.locator(".explorer-error[role=alert]")).toContainText(
    "একই সংস্করণে চলছে না",
  );
  await expect(
    page.getByRole("heading", { name: "এই অনুসন্ধানে এলাকা পাওয়া যায়নি" }),
  ).toHaveCount(0);
  await expect(page.getByLabel("কোন এলাকা খুঁজছেন?")).toHaveValue("আম্বরখানা");
  await page.unroute("**/api/directory?**");
  await page
    .getByRole("button", { name: "আবার চেষ্টা করুন", exact: true })
    .click();
  await expect(page.locator(".directory-results")).toContainText("Ambarkhana");
  await expect(page.locator(".explorer-error[role=alert]")).toHaveCount(0);
});

test("obsolete searches never replace newer results and pagination/filtering use the real API", async ({
  page,
}) => {
  let release: (() => void) | undefined;
  const held = new Promise<void>((resolve) => {
    release = resolve;
  });
  let intercepted = false;
  await page.route("**/api/directory?**", async (route) => {
    const url = new URL(route.request().url());
    if (url.searchParams.get("search") === "Ambarkhana") {
      intercepted = true;
      await held;
    }
    await route.continue().catch(() => {}); // An obsolete fetch is deliberately aborted.
  });
  await page.goto("/areas");
  const input = page.getByLabel("কোন এলাকা খুঁজছেন?");
  await input.fill("Ambarkhana");
  await expect.poll(() => intercepted).toBe(true);
  await input.fill("বালাগঞ্জ");
  await expect(page.locator(".directory-results")).toContainText("বালাগঞ্জ");
  release!();
  await expect(page.locator(".directory-results")).not.toContainText(
    "Ambarkhana",
  );
  await input.fill("");
  await page.getByLabel("ধরন", { exact: true }).selectOption("village");
  await expect(page.locator(".directory-results > li")).toHaveCount(12);
  const first = await page.locator(".directory-results h3").allTextContents();
  const nextResponse = page.waitForResponse((response) => {
    const url = new URL(response.url());
    return (
      url.pathname === "/api/directory" &&
      url.searchParams.get("page") === "2" &&
      url.searchParams.get("kind") === "village"
    );
  });
  await page.getByRole("button", { name: "পরের পৃষ্ঠা" }).click();
  await expect(page).toHaveURL(/page=2/);
  const next = await (await nextResponse).json();
  expect(next.page).toBe(2);
  const names = next.items.map(
    (row: { name_bn: string | null; name_en: string | null }) =>
      row.name_bn || row.name_en,
  );
  expect(names).not.toEqual(first);
  await expect(page.locator(".directory-results h3")).toHaveText(names);
});
