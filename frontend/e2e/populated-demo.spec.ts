import { test, expect } from "@playwright/test";
import { readFileSync } from "node:fs";

test.use({ baseURL: "http://127.0.0.1:5174" });
test.skip(
  !process.env.GRIDWATCH_DEMO_CREDENTIALS,
  "Requires the separately launched private demo, never the normal test/user DB",
);
for (const width of [390, 1440]) {
  test(`populated private demo, real login/default/schedules/history/conflicts/admin/logout at ${width}px`, async ({
    page,
  }) => {
    const records = JSON.parse(
      readFileSync(process.env.GRIDWATCH_DEMO_CREDENTIALS!, "utf8"),
    ).accounts as { role: string; email: string; password: string }[];
    const errors: string[] = [];
    page.on("pageerror", (error) => errors.push(error.message));
    await page.setViewportSize({ width, height: 1000 });
    const user = records.find((x) => x.role === "user")!;
    await page.goto("/login");
    await page.locator("input[name=email]").fill(user.email);
    await page.locator("input[name=password]").fill(user.password);
    await page
      .getByRole("button", { name: "প্রবেশ করুন", exact: true })
      .click();
    await expect(
      page.getByRole("heading", { name: "স্বাগতম, কাল্পনিক ডেমো user" }),
    ).toBeVisible();
    await expect(page.getByText(/বিচ্ছিন্ন অনুশীলন পরিবেশ/)).toBeVisible();
    await expect(
      page.getByText("কাল্পনিক ডেমো — অনুশীলনের ঘোষিত সময়সূচি").first(),
    ).toBeVisible();
    await expect(
      page.getByText("আপনার ব্যক্তিগত পুনঃসংযোগ রেকর্ড হয়েছে"),
    ).toBeVisible();
    const savedResponse = await page.request.get("/api/notices");
    expect((await savedResponse.json()).total).toBe(1);
    await page.reload();
    await expect(
      page.getByText("আপনার ব্যক্তিগত পুনঃসংযোগ রেকর্ড হয়েছে"),
    ).toBeVisible();
    await page
      .getByRole("link", { name: /কাজের সময়/ })
      .first()
      .click();
    const activity = page.locator(".record").filter({
      has: page.getByText("কাল্পনিক ডেমো: অনলাইন ক্লাস", { exact: true }),
    });
    await expect(activity).toBeVisible();
    await activity
      .getByRole("button", { name: "খুলুন ও নতুন করে পরীক্ষা" })
      .click();
    await expect(
      page.getByRole("heading", {
        name: "আপনার কাজ ঘোষিত বিদ্যুৎ-বিরতির সময়ের সঙ্গে মিলেছে",
      }),
    ).toBeVisible();
    await expect(page.getByText(/৬০ মিনিট/).first()).toBeVisible();
    await page
      .getByRole("link", { name: /আমার ইতিহাস/ })
      .first()
      .click();
    await page
      .getByLabel("বিভাগ", { exact: true })
      .selectOption({ label: "কাল্পনিক ডেমো বিভাগ · division" });
    for (const label of [
      "কাল্পনিক ডেমো জেলা · district",
      "কাল্পনিক ডেমো সিটি কর্পোরেশন · city_corporation",
      "কাল্পনিক ডেমো ওয়ার্ড · ward",
      "কাল্পনিক ডেমো মহল্লা ক · neighborhood",
    ]) {
      await page
        .getByLabel("পরের প্রশাসনিক স্তর", { exact: true })
        .last()
        .selectOption({ label });
    }
    await expect(
      page.getByRole("heading", { name: "রেকর্ডভিত্তিক ব্যক্তিগত সারাংশ" }),
    ).toBeVisible();
    await expect(
      page.getByText("৬০ মিনিট", { exact: true }).first(),
    ).toBeVisible();
    expect(
      await page.evaluate(
        () => document.documentElement.scrollWidth > innerWidth,
      ),
    ).toBe(false);
    await page.getByRole("button", { name: "লগআউট", exact: true }).click();
    const admin = records.find((x) => x.role === "admin")!;
    await page.locator("input[name=email]").fill(admin.email);
    await page.locator("input[name=password]").fill(admin.password);
    await page
      .getByRole("button", { name: "প্রবেশ করুন", exact: true })
      .click();
    await expect(
      page.getByRole("heading", { name: "স্বাগতম, কাল্পনিক ডেমো admin" }),
    ).toBeVisible();
    await page.goto("/admin?tab=notices");
    await expect(
      page.getByText("কাল্পনিক ডেমো — শুধু Admin-এর খসড়া").first(),
    ).toBeVisible();
    await page.getByRole("button", { name: "লগআউট", exact: true }).click();
    await expect(
      page.getByRole("heading", { name: "অ্যাকাউন্টে প্রবেশ" }),
    ).toBeVisible();
    expect(await page.evaluate(() => "__gridwatchTest" in window)).toBe(false);
    expect(errors).toEqual([]);
  });
}
