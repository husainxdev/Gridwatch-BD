import { test, expect } from "@playwright/test";

for (const width of [1440, 390]) {
  test(`signup, cascade, saved ownership, session restore and logout at ${width}px`, async ({
    page,
  }) => {
    await page.setViewportSize({ width, height: 900 });
    const errors: string[] = [];
    page.on("pageerror", (e) => errors.push(e.message));
    const email = `browser-${width}-${Date.now()}@example.com`;
    const password = "browser-only-test-password";
    await page.goto("/dashboard");
    await expect(
      page.getByRole("heading", { name: "অ্যাকাউন্টে প্রবেশ" }),
    ).toBeVisible();
    await page.getByRole("link", { name: "নিবন্ধন", exact: true }).click();
    await page.locator("input[name=name]").fill("Browser Test");
    await page.locator("input[name=email]").fill(email);
    await page.locator("input[name=password]").fill(password);
    await page.getByRole("button", { name: "অ্যাকাউন্ট খুলুন" }).click();
    await expect(
      page.getByRole("heading", { name: "স্বাগতম, Browser Test" }),
    ).toBeVisible();
    await page
      .getByLabel("বিভাগ", { exact: true })
      .selectOption({ label: "পরীক্ষামূলক বিভাগ · division" });
    await page
      .getByLabel("পরের প্রশাসনিক স্তর", { exact: true })
      .selectOption({ label: "পরীক্ষামূলক জেলা · district" });
    await page
      .getByRole("button", { name: "এলাকা সংরক্ষণ", exact: true })
      .click();
    await expect(
      page.getByRole("button", { name: "সরান", exact: true }),
    ).toBeVisible();
    await page.getByRole("link", { name: /নোটিশ/ }).first().click();
    await page
      .getByRole("link", { name: /ড্যাশবোর্ড/ })
      .first()
      .click();
    await expect(
      page
        .getByRole("navigation", { name: "এলাকার পূর্বসূরি" })
        .getByRole("button", { name: "পরীক্ষামূলক জেলা" }),
    ).toBeVisible();
    await page.getByRole("button", { name: "শুরু", exact: true }).click();
    await expect(
      page.getByRole("button", { name: "এলাকা সংরক্ষণ", exact: true }),
    ).toHaveCount(0);
    await page
      .getByLabel("এলাকার নাম বা ID খুঁজুন")
      .fill("Browser district alias");
    await page
      .getByRole("button", { name: /পরীক্ষামূলক বিভাগ \/ পরীক্ষামূলক জেলা/ })
      .click();
    await expect(
      page.getByRole("button", { name: "এলাকা সংরক্ষণ", exact: true }),
    ).toBeVisible();
    // Force two expired responses, including one arriving after refresh completed.
    // Retried requests still go to the real authenticated backend.
    let refreshCount = 0;
    page.on("request", (r) => {
      if (r.url().endsWith("/api/auth/refresh")) refreshCount++;
    });
    const refreshResponse = page.waitForResponse(
      (r) => r.url().endsWith("/api/auth/refresh") && r.status() === 200,
    );
    let failures = 0;
    await page.route("**/api/auth/me", async (route) => {
      const attempt = ++failures;
      if (attempt <= 2) {
        if (attempt === 2) await refreshResponse;
        await route.fulfill({
          status: 401,
          contentType: "application/json",
          body: JSON.stringify({ detail: "Expired access test" }),
        });
      } else await route.continue();
    });
    const users = await page.evaluate(async () => {
      const { api } = window.__gridwatchTest!;
      return Promise.all([api("/api/auth/me"), api("/api/auth/me")]);
    });
    expect(users[0].email).toBe(email);
    expect(users[1].email).toBe(email);
    expect(refreshCount).toBe(1);
    await page.unroute("**/api/auth/me");
    await page.reload();
    await expect(
      page.getByRole("heading", { name: "স্বাগতম, Browser Test" }),
    ).toBeVisible();
    await expect(
      page.getByRole("button", { name: "সরান", exact: true }),
    ).toBeVisible();
    expect(
      await page.evaluate(() => localStorage.length + sessionStorage.length),
    ).toBe(0);
    expect(
      await page.evaluate(
        () => document.documentElement.scrollWidth > innerWidth,
      ),
    ).toBe(false);
    await page.getByRole("button", { name: "লগআউট", exact: true }).click();
    await expect(
      page.getByRole("heading", { name: "অ্যাকাউন্টে প্রবেশ" }),
    ).toBeVisible();
    await page.locator("input[name=email]").fill(email);
    await page.locator("input[name=password]").fill(password);
    await page
      .getByRole("button", { name: "প্রবেশ করুন", exact: true })
      .click();
    await expect(
      page.getByRole("heading", { name: "স্বাগতম, Browser Test" }),
    ).toBeVisible();
    await page.getByRole("button", { name: "সরান", exact: true }).click();
    await expect(
      page.getByRole("button", { name: "সরান", exact: true }),
    ).toHaveCount(0);
    await page.getByRole("button", { name: "লগআউট", exact: true }).click();
    await expect(
      page.getByRole("heading", { name: "অ্যাকাউন্টে প্রবেশ" }),
    ).toBeVisible();
    expect(errors).toEqual([]);
  });
}
