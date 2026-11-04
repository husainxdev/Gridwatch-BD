import { test, expect } from "@playwright/test";
import AxeBuilder from "@axe-core/playwright";

test("supplied current and census directories remain distinct through real API and browser", async ({
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
    page.getByRole("heading", {
      name: "উপজেলা, ইউনিয়ন, গ্রাম ও মহল্লা খুঁজুন",
    }),
  ).toBeVisible();
  await page.getByLabel("তালিকায় নাম খুঁজুন").fill("বালাগঞ্জ");
  await page.getByRole("button", { name: "খুঁজুন", exact: true }).click();
  await expect(page.locator(".directory-results")).toContainText("বালাগঞ্জ");
  await expect(
    page
      .locator(".directory-results")
      .getByRole("link", { name: "এলাকার বিদ্যুৎ তথ্য →" })
      .first(),
  ).toBeVisible();
  await page.getByRole("button", { name: "উপ-এলাকা (৬)", exact: true }).click();
  await expect(page.locator(".directory-results > li")).toHaveCount(6);
  await expect(
    page.getByRole("navigation", { name: "তালিকার পূর্বসূরি" }),
  ).toContainText("বালাগঞ্জ");
  await page.getByRole("button", { name: /গ্রাম \/ মহল্লা · ২০২২/ }).click();
  await page.getByLabel("তালিকায় নাম খুঁজুন").fill("আম্বরখানা");
  await page.getByRole("button", { name: "খুঁজুন", exact: true }).click();
  await expect(page.locator(".directory-results")).toContainText("Ambarkhana");
  await expect(page.locator(".directory-warning")).toContainText(
    "বর্তমান রিপোর্টের এলাকা নয়",
  );
  await expect(
    page
      .locator(".directory-results")
      .getByRole("link", { name: "এলাকার বিদ্যুৎ তথ্য →" }),
  ).toHaveCount(0);
  await expect(page.locator(".directory-results")).toContainText(
    "Airport Thana",
  );
  await expect(
    page
      .locator(".directory-results")
      .getByRole("link", { name: "দেওয়া PDF লিংক ↗" })
      .first(),
  ).toHaveAttribute("href", /#page=164$/);
  for (const branch of ["portal", "census2022"]) {
    await page.goto(
      "/areas?" +
        new URLSearchParams({
          branch,
          search: branch === "portal" ? "বালাগঞ্জ" : "আম্বরখানা",
        }),
    );
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
  const after = await (
    await request.get("/api/directory?branch=census2022&search=Ambarkhana")
  ).json();
  expect(
    after.items.every(
      (row: { reportable: boolean; location_id: string | null }) =>
        !row.reportable && row.location_id === null,
    ),
  ).toBe(true);
  await page.goto("/?location_id=");
  await page.getByLabel("এলাকার নাম খুঁজুন").fill("আম্বরখানা");
  await page.getByRole("link", { name: /বর্তমান তালিকায় নেই/ }).click();
  await expect(page).toHaveURL(/\/areas\?branch=census2022&search=/);
  await expect(page.locator(".directory-results")).toContainText("Ambarkhana");
  expect(errors).toEqual([]);
});
