import { test, expect } from "@playwright/test";

test.use({ baseURL: "http://127.0.0.1:5174" });
test.skip(
  !process.env.GRIDWATCH_DEMO_MAILBOX,
  "Requires the loopback Mailpit of the private local demo",
);
test("local demo Mailpit reset is single-use and old sessions are revoked", async ({
  page,
  request,
}) => {
  const mailbox = new URL(process.env.GRIDWATCH_DEMO_MAILBOX!);
  expect(["127.0.0.1", "localhost", "[::1]"]).toContain(mailbox.hostname);
  const email = `fictional-demo-reset-${crypto.randomUUID()}@example.com`;
  const oldPassword = crypto.randomUUID(),
    newPassword = crypto.randomUUID();
  const registration = await request.post("/api/auth/register", {
    data: {
      email,
      password: oldPassword,
      display_name: "Fictional demo reset check",
    },
  });
  expect(registration.status()).toBe(201);
  const access = (await registration.json()).access_token;
  await page.goto("/forgot");
  await page.getByLabel("ইমেইল", { exact: true }).fill(email);
  const submitted = page.waitForResponse((r) =>
    r.url().endsWith("/api/auth/password-reset/request"),
  );
  await page.getByRole("button", { name: "রিসেট লিংক পাঠান" }).click();
  expect((await submitted).status()).toBe(202);
  let messageId = "";
  await expect
    .poll(async () => {
      const response = await request.get(
        `${mailbox.origin}/api/v1/search?query=${encodeURIComponent("to:" + email)}`,
      );
      const found = await response.json();
      messageId = found.messages?.[0]?.ID || "";
      return !!messageId;
    })
    .toBe(true);
  const message = await (
    await request.get(`${mailbox.origin}/api/v1/message/${messageId}`)
  ).json();
  const link = String(message.Text).match(
    /http:\/\/127\.0\.0\.1:5174\/reset#token=\S+/,
  )?.[0];
  expect(!!link).toBe(true); // Never include the link/token in assertion output.
  await page.evaluate((url) => window.location.assign(url!), link);
  await expect
    .poll(
      () =>
        new URL(page.url()).pathname === "/reset" &&
        new URL(page.url()).hash === "",
    )
    .toBe(true);
  await page.getByLabel("পাসওয়ার্ড", { exact: true }).fill(newPassword);
  await page.getByRole("button", { name: "পাসওয়ার্ড বদলান" }).click();
  await expect(page).toHaveURL(/\/login$/);
  expect(
    (
      await request.get("/api/auth/me", {
        headers: { Authorization: "Bearer " + access },
      })
    ).status(),
  ).toBe(401);
  await page.evaluate((url) => window.location.assign(url!), link);
  await page
    .getByLabel("পাসওয়ার্ড", { exact: true })
    .fill(crypto.randomUUID());
  await page.getByRole("button", { name: "পাসওয়ার্ড বদলান" }).click();
  await expect(page.locator("main").getByRole("alert")).toContainText(
    "Invalid or expired reset link",
  );
  expect(
    (
      await request.post("/api/auth/login", {
        data: { email, password: oldPassword },
      })
    ).status(),
  ).toBe(401);
  expect(
    (
      await request.post("/api/auth/login", {
        data: { email, password: newPassword },
      })
    ).status(),
  ).toBe(200);
});
