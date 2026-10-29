import { test, expect, request } from "@playwright/test";

async function signup(page, suffix: string) {
  await page.goto("/register");
  await page.locator("input[name=name]").fill("Dashboard " + suffix);
  await page
    .locator("input[name=email]")
    .fill(`dash-${suffix}-${Date.now()}@example.com`);
  await page.locator("input[name=password]").fill("dashboard-test-password");
  await page.getByRole("button", { name: "অ্যাকাউন্ট খুলুন" }).click();
  await expect(
    page.getByRole("heading", { name: "স্বাগতম, Dashboard " + suffix }),
  ).toBeVisible();
}
async function select(page, alias = "Browser district alias") {
  await page.getByLabel("এলাকার নাম বা ID খুঁজুন").fill(alias);
  await page
    .getByRole("button", {
      name: alias.startsWith("Alternate")
        ? /পরীক্ষামূলক বিভাগ \/ দ্বিতীয় পরীক্ষামূলক জেলা/
        : /পরীক্ষামূলক বিভাগ \/ পরীক্ষামূলক জেলা/,
    })
    .click();
  await expect(page.getByText("দেখছেন:", { exact: false })).toBeVisible();
}
for (const width of [1440, 390]) {
  test(`saved default, mixed evidence and persisted personal timer ${width}px`, async ({
    page,
  }) => {
    await page.setViewportSize({ width, height: 900 });
    await page.emulateMedia({ reducedMotion: "reduce" });
    await signup(page, String(width));
    await select(page);
    await page
      .getByRole("button", { name: "এলাকা সংরক্ষণ", exact: true })
      .click();
    const saved = page.locator(".saved-area");
    await saved.getByLabel("এলাকার সংক্ষিপ্ত নাম").fill("বাসা");
    await saved
      .getByRole("button", { name: "ডিফল্ট করুন", exact: true })
      .click();
    await expect(
      saved.getByRole("button", { name: /বাসা · পরীক্ষামূলক জেলা · ডিফল্ট/ }),
    ).toBeVisible();
    await page.reload();
    await expect(
      page.getByText("দেখছেন: পরীক্ষামূলক জেলা", { exact: true }),
    ).toBeVisible();
    await page
      .getByRole("button", { name: "এলাকা সংরক্ষণ", exact: true })
      .click();
    await expect(page.getByText("এলাকাটি আগে থেকেই সংরক্ষিত")).toBeVisible();
    const area = await page.evaluate(async () => {
      const { api } = window.__gridwatchTest!;
      const a = (await api("/api/saved-areas")).items[0];
      await api("/api/reports", {
        method: "POST",
        body: JSON.stringify({
          location_id: a.id,
          kind: "power_off",
          observed_at: new Date(Date.now() - 20 * 60000).toISOString(),
          idempotency_key: crypto.randomUUID(),
        }),
      });
      return a.id;
    });
    const other = await request.newContext({
      baseURL: "http://localhost:15173",
    });
    const registration = await other.post("/api/auth/register", {
      data: {
        email: `other-${width}-${Date.now()}@example.com`,
        password: "independent-password",
        display_name: "Other observer",
      },
    });
    expect(registration.status()).toBe(201);
    const token = (await registration.json()).access_token;
    const restoration = await other.post("/api/reports", {
      headers: { Authorization: `Bearer ${token}` },
      data: {
        location_id: area,
        kind: "power_back",
        observed_at: new Date().toISOString(),
        idempotency_key: crypto.randomUUID(),
      },
    });
    expect(restoration.status()).toBe(201);
    await page
      .getByRole("button", { name: "রিপোর্ট ও ইতিহাস রিফ্রেশ" })
      .click();
    await expect(
      page.getByRole("heading", {
        name: "মিশ্র রিপোর্ট — কারও ফিরেছে, কারও নেই",
      }),
    ).toBeVisible();
    await expect(page.getByTestId("episode-duration")).toContainText(
      "২০ মিনিট",
    );
    await page
      .getByRole("button", { name: "আমার এখনো আসেনি", exact: true })
      .click();
    await expect(
      page.getByText("আপনার সংযোগের রিপোর্ট জমা হয়েছে"),
    ).toBeVisible();
    const identity = await page.evaluate(async () => {
      const { api } = window.__gridwatchTest!;
      return (await api("/api/me/episodes")).items[0];
    });
    await page.reload();
    await expect(page.getByTestId("episode-duration")).toContainText(
      "২০ মিনিট",
    );
    await expect(
      page.getByText("আপনার বিভ্রাট এখনো বন্ধ করা হয়নি", { exact: true }),
    ).toBeVisible();
    await page
      .getByRole("button", { name: "বিদ্যুৎ ফিরেছে", exact: true })
      .click();
    await expect(
      page.getByText("আপনার ব্যক্তিগত পুনঃসংযোগ রেকর্ড হয়েছে"),
    ).toBeVisible();
    const closed = await page.evaluate(async () => {
      const { api } = window.__gridwatchTest!;
      return (await api("/api/me/episodes")).items[0];
    });
    expect(closed.id).toBe(identity.id);
    expect(closed.started_at).toBe(identity.started_at);
    expect(closed.is_open).toBe(false);
    const others = (
      await (
        await other.get("/api/me/episodes", {
          headers: { Authorization: `Bearer ${token}` },
        })
      ).json()
    ).items;
    expect(others).toHaveLength(1);
    expect(others[0].started_at).toBeNull();
    await other.dispose();
    await page.screenshot({
      path: `/tmp/gridwatch-dashboard-7-8-${width}.png`,
      fullPage: true,
    });
    expect(
      await page.evaluate(
        () => document.documentElement.scrollWidth > innerWidth,
      ),
    ).toBe(false);
    // Native controls remain keyboard-operable.
    await page
      .getByRole("button", { name: "রিপোর্ট ও ইতিহাস রিফ্রেশ" })
      .focus();
    await expect(
      page.getByRole("button", { name: "রিপোর্ট ও ইতিহাস রিফ্রেশ" }),
    ).toBeFocused();
    await page.keyboard.press("Enter");
    await saved.getByRole("button", { name: "সরান", exact: true }).click();
    await expect(
      page.getByText(
        "নির্বাচিত সংরক্ষিত এলাকাটি সরানো হয়েছে। নতুন এলাকা নিজে বাছুন।",
      ),
    ).toBeVisible();
    await expect(
      page.getByText("দেখছেন: পরীক্ষামূলক জেলা", { exact: true }),
    ).toHaveCount(0);
  });
}

test("rapid area switch, stale failure, refresh expiry and logout isolate private data", async ({
  page,
}) => {
  await signup(page, "network");
  await select(page);
  const original = await page.evaluate(async () => {
    const { api } = window.__gridwatchTest!;
    return (await api("/api/locations?search=Browser%20test%20district"))
      .items[0].id;
  });
  // Keep a previous area's response in flight while the next area is selected.
  let release!: () => void;
  const gate = new Promise<void>((resolve) => (release = resolve));
  let completed!: () => void;
  const handled = new Promise<void>((resolve) => (completed = resolve));
  let observed!: () => void;
  const arrived = new Promise<void>((resolve) => (observed = resolve));
  await page.route("**/api/dashboard?**", async (route) => {
    if (route.request().url().includes(original)) {
      const response = await route.fetch();
      observed();
      await gate;
      try {
        await route.fulfill({ response });
      } finally {
        completed();
      }
    } else await route.continue();
  });
  await page.getByRole("button", { name: "রিপোর্ট ও ইতিহাস রিফ্রেশ" }).click();
  await arrived;
  await page.getByRole("button", { name: "শুরু", exact: true }).click();
  await select(page, "Alternate area alias");
  await expect(
    page.getByText("দেখছেন: দ্বিতীয় পরীক্ষামূলক জেলা", { exact: true }),
  ).toBeVisible();
  release();
  await handled;
  await page.unroute("**/api/dashboard?**");
  await expect(
    page.getByText("দেখছেন: পরীক্ষামূলক জেলা", { exact: true }),
  ).toHaveCount(0);
  await page.route("**/api/dashboard?**", (route) =>
    route.fulfill({
      status: 503,
      contentType: "application/json",
      body: JSON.stringify({ detail: "Test network unavailable" }),
    }),
  );
  await page.getByRole("button", { name: "রিপোর্ট ও ইতিহাস রিফ্রেশ" }).click();
  await expect(page.locator("main").getByRole("alert")).toContainText(
    "Test network unavailable",
  );
  await expect(
    page.getByText("দেখছেন: দ্বিতীয় পরীক্ষামূলক জেলা", { exact: true }),
  ).toBeVisible();
  await expect(
    page.getByText("তথ্য হালনাগাদ হয়নি — আগের তথ্য দেখানো হচ্ছে।").first(),
  ).toBeVisible();
  await expect(
    page.getByRole("button", { name: "বিদ্যুৎ নেই", exact: true }),
  ).toBeDisabled();
  await page.unroute("**/api/dashboard?**");
  await page.getByRole("button", { name: "রিপোর্ট ও ইতিহাস রিফ্রেশ" }).click();
  await expect(page.locator("main").getByRole("alert")).toHaveCount(0);
  // A failed startup refresh must clear all private query entries.
  await page.route("**/api/auth/refresh", (route) =>
    route.fulfill({
      status: 401,
      contentType: "application/json",
      body: JSON.stringify({ detail: "Revoked session test" }),
    }),
  );
  await page.route("**/api/dashboard?**", (route) =>
    route.fulfill({
      status: 401,
      contentType: "application/json",
      body: JSON.stringify({ detail: "Expired access test" }),
    }),
  );
  await page.getByRole("button", { name: "রিপোর্ট ও ইতিহাস রিফ্রেশ" }).click();
  await expect(
    page.getByRole("heading", { name: "অ্যাকাউন্টে প্রবেশ" }),
  ).toBeVisible();
  await expect(
    page.getByText("দেখছেন: দ্বিতীয় পরীক্ষামূলক জেলা", { exact: true }),
  ).toHaveCount(0);
  await page.unroute("**/api/auth/refresh");
  await page.unroute("**/api/dashboard?**");
  // The mocked 401 did not revoke the server cookie; finish that real session
  // before creating a new account, so a startup refresh cannot restore it.
  await page.evaluate(async () => {
    const { api } = window.__gridwatchTest!;
    await api("/api/auth/logout", { method: "POST" }, false);
  });
  await signup(page, "fresh-user");
  await expect(page.getByText("দেখছেন:", { exact: false })).toHaveCount(0);
  await expect(
    page.getByRole("heading", { name: "এখনো সংরক্ষিত এলাকা নেই" }),
  ).toBeVisible();
  await select(page);
  await page
    .getByRole("button", { name: "আমার এখনো আসেনি", exact: true })
    .click();
  await expect(page.getByTestId("episode-duration")).toHaveText(
    "শুরুর সময় অজানা",
  );
  await page.getByRole("button", { name: "লগআউট", exact: true }).click();
  await expect(
    page.getByRole("heading", { name: "অ্যাকাউন্টে প্রবেশ" }),
  ).toBeVisible();
});

test("shared polling deduplicates, backs off, and pauses while hidden or offline", async ({
  page,
}) => {
  await signup(page, "polling");
  await select(page);
  await page.clock.install();
  await page.clock.pauseAt(new Date());
  const interval = await page.evaluate(async () => {
    return window.__gridwatchTest!.pollInterval;
  });
  let calls = 0;
  let fail = false;
  let release!: () => void;
  let arrived!: () => void;
  const gate = new Promise<void>((resolve) => (release = resolve)),
    waiting = new Promise<void>((resolve) => (arrived = resolve));
  await page.route("**/api/dashboard?**", async (route) => {
    calls++;
    if (calls === 1) {
      arrived();
      await gate;
    }
    if (fail)
      await route.fulfill({
        status: 503,
        contentType: "application/json",
        body: JSON.stringify({ detail: "Controlled polling failure" }),
      });
    else await route.continue();
  });
  await page.getByRole("button", { name: "রিপোর্ট ও ইতিহাস রিফ্রেশ" }).click();
  await waiting;
  await page.getByRole("button", { name: "রিপোর্ট ও ইতিহাস রিফ্রেশ" }).click();
  expect(calls).toBe(1);
  const first = page.waitForResponse(
    (r) => r.url().includes("/api/dashboard?") && r.status() === 200,
  );
  release();
  await first;
  fail = true;
  await page.getByRole("button", { name: "রিপোর্ট ও ইতিহাস রিফ্রেশ" }).click();
  await expect(page.locator("main").getByRole("alert")).toContainText(
    "Controlled polling failure",
  );
  expect(calls).toBe(2);
  await page.clock.fastForward(interval * 2 - 1000);
  expect(calls).toBe(2);
  await page.clock.fastForward(2000);
  await expect.poll(() => calls).toBe(3);
  await page.evaluate(() => {
    Object.defineProperty(document, "hidden", {
      configurable: true,
      value: true,
    });
    document.dispatchEvent(new Event("visibilitychange"));
  });
  await page.clock.fastForward(300000);
  expect(calls).toBe(3);
  fail = false;
  await page.evaluate(() => {
    Object.defineProperty(document, "hidden", {
      configurable: true,
      value: false,
    });
    document.dispatchEvent(new Event("visibilitychange"));
  });
  await expect.poll(() => calls).toBe(4);
  await expect(page.locator("main").getByRole("alert")).toHaveCount(0);
  await page.evaluate(() => {
    Object.defineProperty(navigator, "onLine", {
      configurable: true,
      value: false,
    });
    window.dispatchEvent(new Event("offline"));
  });
  await expect(page.locator("main").getByRole("alert")).toContainText(
    "ইন্টারনেট সংযোগ নেই",
  );
  await page.clock.fastForward(interval * 5);
  expect(calls).toBe(4);
  await page.evaluate(() => {
    Object.defineProperty(navigator, "onLine", {
      configurable: true,
      value: true,
    });
    window.dispatchEvent(new Event("online"));
  });
  await expect.poll(() => calls).toBe(5);
  await expect(page.locator("main").getByRole("alert")).toHaveCount(0);
  await expect(
    page.getByText("দেখছেন: পরীক্ষামূলক জেলা", { exact: true }),
  ).toBeVisible();
});

test("unavailable saved default has an explicit fallback without choosing another area", async ({
  page,
}) => {
  await signup(page, "unavailable");
  await select(page);
  await page
    .getByRole("button", { name: "এলাকা সংরক্ষণ", exact: true })
    .click();
  await page
    .locator(".saved-area")
    .getByRole("button", { name: "ডিফল্ট করুন", exact: true })
    .click();
  await expect(
    page
      .locator(".saved-area")
      .getByRole("button", { name: "ডিফল্ট সরান", exact: true }),
  ).toBeVisible();
  const other = await request.newContext({ baseURL: "http://localhost:15173" });
  const login = await other.post("/api/auth/login", {
    data: {
      email: "phase-admin@example.com",
      password: process.env.BROWSER_TEST_PASSWORD!,
    },
  });
  expect(login.status()).toBe(200);
  const token = (await login.json()).access_token;
  const area = (
    await (
      await other.get("/api/locations?search=Browser%20test%20district")
    ).json()
  ).items[0];
  const body = {
    version: area.version,
    name_bn: area.name_bn,
    name_en: area.name_en,
    slug: area.slug,
    kind: area.kind,
    parent_id: area.parent_id,
    aliases: area.aliases,
  };
  try {
    expect(
      (
        await other.put("/api/admin/locations/" + area.id, {
          headers: { Authorization: `Bearer ${token}` },
          data: body,
        })
      ).status(),
    ).toBe(200);
    await page.reload();
    await expect(
      page.getByText(
        "আপনার ডিফল্ট এলাকাটি এখন উপলব্ধ নয়। নিজে একটি যাচাইকৃত এলাকা বাছুন।",
      ),
    ).toBeVisible();
    await expect(page.getByText("দেখছেন:", { exact: false })).toHaveCount(0);
    await expect(
      page.getByRole("button", { name: "বিদ্যুৎ নেই", exact: true }),
    ).toHaveCount(0);
    await page
      .locator(".saved-area")
      .getByRole("button", { name: "সরান", exact: true })
      .click();
    await expect(
      page.getByRole("heading", { name: "এখনো সংরক্ষিত এলাকা নেই" }),
    ).toBeVisible();
  } finally {
    expect(
      (
        await other.post("/api/admin/locations/" + area.id + "/verify", {
          headers: { Authorization: `Bearer ${token}` },
          data: {
            source_url: "https://example.com/fictional-test-only",
            version: area.version + 1,
          },
        })
      ).status(),
    ).toBe(200);
    await other.dispose();
  }
});
