import { test, expect } from "@playwright/test";
test("large saved collection pages preserve selection and activity picker access", async ({
  page,
}) => {
  await page.setViewportSize({ width: 390, height: 800 });
  await page.goto("/login");
  await page.getByLabel("ইমেইল", { exact: true }).fill("qa-many@example.com");
  await page
    .getByLabel("পাসওয়ার্ড", { exact: true })
    .fill(process.env.BROWSER_TEST_PASSWORD!);
  await page.getByRole("button", { name: "প্রবেশ করুন", exact: true }).click();
  await expect(
    page.getByRole("heading", { name: "স্বাগতম, Fictional QA paging user" }),
  ).toBeVisible();
  await expect(page.locator(".saved-area")).toHaveCount(100);
  await expect(
    page.getByRole("button", { name: "বিদ্যুৎ নেই", exact: true }),
  ).toBeEnabled();
  await page
    .getByRole("button", { name: "আরও সংরক্ষিত এলাকা", exact: true })
    .click();
  await expect(page.locator(".saved-area")).toHaveCount(5);
  await expect(
    page.getByRole("button", { name: "বিদ্যুৎ নেই", exact: true }),
  ).toBeEnabled();
  const hundred = page
    .locator(".saved-area")
    .filter({ hasText: "কাল্পনিক QA এলাকা 100" });
  await hundred
    .getByRole("button", { name: "ডিফল্ট করুন", exact: true })
    .click();
  await expect(page.locator(".saved-area")).toHaveCount(5);
  await expect(
    page.getByRole("button", { name: "বিদ্যুৎ নেই", exact: true }),
  ).toBeEnabled();
  const oldArea = page
    .locator(".saved-area")
    .filter({ hasText: "কাল্পনিক QA এলাকা 101" });
  await oldArea.locator(".saved-switch").click();
  await expect(page.locator(".selected-area strong")).toHaveText(
    "দেখছেন: কাল্পনিক QA এলাকা 101",
  );
  let release!: () => void;
  let arrived!: () => void;
  const gate = new Promise<void>((resolve) => {
    release = resolve;
  });
  const waiting = new Promise<void>((resolve) => {
    arrived = resolve;
  });
  await page.route("**/api/saved-areas/*", async (route) => {
    if (route.request().method() !== "DELETE") return route.continue();
    arrived();
    await gate;
    await route.continue();
  });
  try {
    await oldArea.getByRole("button", { name: "সরান", exact: true }).click();
    await waiting;
    await page
      .locator(".saved-area")
      .filter({ hasText: "কাল্পনিক QA এলাকা 102" })
      .locator(".saved-switch")
      .click();
    await expect(page.locator(".selected-area strong")).toHaveText(
      "দেখছেন: কাল্পনিক QA এলাকা 102",
    );
    release();
    await expect(page.locator(".saved-area")).toHaveCount(4);
    await expect(page.locator(".selected-area strong")).toHaveText(
      "দেখছেন: কাল্পনিক QA এলাকা 102",
    );
  } finally {
    release();
  }
  await page.goto("/activities");
  await page
    .getByRole("button", { name: "আরও সংরক্ষিত এলাকা", exact: true })
    .click();
  await expect(
    page.getByLabel("সংরক্ষিত এলাকা", { exact: true }).locator("option"),
  ).toHaveCount(5);
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= innerWidth,
    ),
  ).toBe(true);
});
