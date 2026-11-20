// Isolated UI regression; synthetic OCR response, no customer photos in fixtures.
const { chromium } = require("playwright");
const assert = require("node:assert/strict");
(async () => {
  const baseUrl = process.env.COUNTER_TEST_URL;
  assert.ok(baseUrl, "Set COUNTER_TEST_URL to a new temporary ledger server");
  const browser = await chromium.launch({ channel: "chrome", headless: true });
  try {
    const page = await browser.newPage();
    const errors = [];
    page.on("pageerror", (error) => errors.push(error.message));
    await page.goto(baseUrl);
    assert.equal(
      (await (await page.request.get(baseUrl + "/api/state")).json()).setup,
      true,
      "Use a new temporary ledger",
    );
    await page.locator(".auth .language-picker").selectOption("en");
    await page.locator("#name").fill("Receipt Test Owner");
    await page.locator("#password").fill("fictional-password-123");
    await page.locator("#authform button").click();
    await page.waitForSelector(".shell");
    const before = await (
      await page.request.get(baseUrl + "/api/state")
    ).json();
    await page.evaluate(() => {
      const revoke = URL.revokeObjectURL.bind(URL);
      window.revokedReceiptUrls = [];
      URL.revokeObjectURL = (url) => {
        window.revokedReceiptUrls.push(url);
        revoke(url);
      };
    });
    const image = Buffer.from(
      "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+aN1kAAAAASUVORK5CYII=",
      "base64",
    );
    for (const duringOCR of [false, true]) {
      let requested;
      const started = new Promise((resolve) => (requested = resolve));
      await page.route("**/api/receipt/extract", async (route) => {
        requested();
        if (duringOCR) await new Promise((resolve) => setTimeout(resolve, 500));
        await route
          .fulfill({
            status: 200,
            contentType: "application/json",
            body: JSON.stringify({
              provider: "KBZPay",
              amount: 1000,
              customer: "Test Customer",
              transaction_type: "cash_in",
            }),
          })
          .catch(() => {});
      });
      await page
        .getByRole("button", { name: "Import receipt photo", exact: true })
        .click();
      await page.locator("#f_image").setInputFiles({
        name: "synthetic.png",
        mimeType: "image/png",
        buffer: image,
      });
      await page
        .getByRole("button", { name: "Read receipt", exact: true })
        .click();
      let deadline;
      try {
        await Promise.race([
          started,
          new Promise((_, reject) => {
            deadline = setTimeout(
              () => reject(Error("OCR request not sent")),
              5000,
            );
          }),
        ]);
      } finally {
        clearTimeout(deadline);
      }
      let preview;
      if (!duringOCR) {
        await page.locator("#f_customer").waitFor();
        preview = await page.locator(".receipt-preview").getAttribute("src");
      }
      await page.getByRole("button", { name: "Cancel", exact: true }).click();
      await page.waitForTimeout(700);
      assert.equal(
        await page.locator("#modal").evaluate((element) => element.open),
        false,
      );
      assert.equal(await page.locator("#modal #form").count(), 0);
      if (preview)
        assert.ok(
          await page.evaluate(
            (url) => window.revokedReceiptUrls.includes(url),
            preview,
          ),
        );
      const after = await (
        await page.request.get(baseUrl + "/api/state")
      ).json();
      assert.deepEqual(after.entries, before.entries);
      assert.deepEqual(after.accounts, before.accounts);
      assert.equal(after.cash, before.cash);
      await page.unroute("**/api/receipt/extract");
    }
    assert.deepEqual(errors, []);
    console.log(
      "PASS: Cancel during/after OCR leaves no record, clears the form, revokes preview and prevents reopening.",
    );
  } finally {
    await browser.close();
  }
})().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
