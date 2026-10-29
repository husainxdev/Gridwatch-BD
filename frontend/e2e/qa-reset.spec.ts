import { test, expect } from "@playwright/test";

test("reset email browser journey is single-use and revokes another live session", async ({
  page,
  browser,
  request,
}) => {
  const email = `qa-reset-${crypto.randomUUID()}@example.com`;
  await page.goto("/register");
  await page.locator("input[name=name]").fill("Fictional QA reset user");
  await page.getByLabel("ইমেইল", { exact: true }).fill(email);
  await page.getByLabel("পাসওয়ার্ড", { exact: true }).fill("qa-old-password");
  await page.getByRole("button", { name: "অ্যাকাউন্ট খুলুন" }).click();
  await expect(
    page.getByRole("heading", { name: "স্বাগতম, Fictional QA reset user" }),
  ).toBeVisible();
  const resetContext = await browser.newContext();
  try {
    const reset = await resetContext.newPage();
    await reset.goto("/forgot");
    await reset.getByLabel("ইমেইল", { exact: true }).fill(email);
    const delivered = reset.waitForResponse((r) =>
      r.url().endsWith("/api/auth/password-reset/request"),
    );
    await reset.getByRole("button", { name: "রিসেট লিংক পাঠান" }).click();
    expect((await delivered).status()).toBe(202);
    await expect(reset.locator("main").getByRole("status")).toContainText(
      "If the account is eligible",
    );
    const message = await request.get(
      `${process.env.QA_MAILBOX_URL}/?recipient=${encodeURIComponent(email)}`,
    );
    expect(message.status()).toBe(200);
    const link = (await message.json()).text.match(
      /http:\/\/localhost:15173\/reset#token=\S+/,
    )[0];
    await reset.evaluate((url) => window.location.assign(url), link);
    await expect
      .poll(
        () =>
          new URL(reset.url()).hash === "" &&
          new URL(reset.url()).pathname === "/reset",
      )
      .toBe(true);
    await reset
      .getByLabel("পাসওয়ার্ড", { exact: true })
      .fill("qa-new-password");
    await reset.getByRole("button", { name: "পাসওয়ার্ড বদলান" }).click();
    await expect(reset).toHaveURL(/\/login$/);
    // Do not return or print credentials: only the protected endpoint's status.
    const revoked = await page.evaluate(async () => {
      try {
        await window.__gridwatchTest!.api("/api/auth/me");
        return 200;
      } catch (error) {
        return (error as { status: number }).status;
      }
    });
    expect(revoked).toBe(401);
    await expect(page).toHaveURL(/\/login$/);
    await reset.evaluate((url) => window.location.assign(url), link);
    await reset
      .getByLabel("পাসওয়ার্ড", { exact: true })
      .fill("qa-third-password");
    await reset.getByRole("button", { name: "পাসওয়ার্ড বদলান" }).click();
    await expect(reset.locator("main").getByRole("alert")).toContainText(
      "Invalid or expired reset link",
    );
    await reset.goto("/login");
    await reset.getByLabel("ইমেইল", { exact: true }).fill(email);
    await reset
      .getByLabel("পাসওয়ার্ড", { exact: true })
      .fill("qa-old-password");
    await reset
      .getByRole("button", { name: "প্রবেশ করুন", exact: true })
      .click();
    await expect(reset.locator("main").getByRole("alert")).toBeVisible();
    await reset
      .getByLabel("পাসওয়ার্ড", { exact: true })
      .fill("qa-new-password");
    await reset
      .getByRole("button", { name: "প্রবেশ করুন", exact: true })
      .click();
    await expect(
      reset.getByRole("heading", { name: "স্বাগতম, Fictional QA reset user" }),
    ).toBeVisible();
  } finally {
    await resetContext.close();
  }
});
