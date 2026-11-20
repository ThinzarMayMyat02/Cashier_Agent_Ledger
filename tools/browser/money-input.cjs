// Run only against a new temporary ledger; this check creates fictional records.
const { chromium } = require("playwright");
const assert = require("node:assert/strict");

async function main() {
  const baseUrl = process.env.COUNTER_TEST_URL;
  assert.ok(
    baseUrl,
    "Set COUNTER_TEST_URL to an isolated Counter test server.",
  );
  const browser = await chromium.launch({ channel: "chrome", headless: true });
  try {
    const page = await browser.newPage();
    const errors = [];
    page.on("pageerror", (error) => errors.push(error.message));
    await page.goto(baseUrl);
    const initial = await page.request.get(baseUrl + "/api/state");
    assert.equal(
      (await initial.json()).setup,
      true,
      "Refusing an initialized ledger. Use a new temporary database.",
    );
    await page.locator(".auth .language-picker").selectOption("en");
    await page.locator("#name").fill("Browser Test Owner");
    await page.locator("#password").fill("Fictional-test-password-123");
    await page.locator("#authform button").click();
    await page.waitForSelector(".shell");

    async function readState() {
      return (await page.request.get(baseUrl + "/api/state")).json();
    }
    async function verifyMoneyInput(selector) {
      const input = page.locator(selector);
      await input.fill("1234");
      assert.equal(await input.inputValue(), "1,234");
      await input.press("End");
      await input.pressSequentially("abcE.+-! ");
      assert.equal(
        await input.inputValue(),
        "1,234",
        "Typed characters must be blocked",
      );
      for (const invalid of ["abc", "1e6", "100.50", "-200", "100 MMK"]) {
        await input.fill(invalid);
        assert.equal(
          await input.inputValue(),
          "1,234",
          "Reject the entire edit: " + invalid,
        );
        assert.equal(
          await input.evaluate((element, text) => {
            const clipboardData = new DataTransfer();
            clipboardData.setData("text/plain", text);
            return element.dispatchEvent(
              new ClipboardEvent("paste", {
                clipboardData,
                bubbles: true,
                cancelable: true,
              }),
            );
          }, invalid),
          false,
          "Reject pasted characters: " + invalid,
        );
      }
      await input.fill("၁၂၃၄၅၆");
      assert.equal(
        await input.inputValue(),
        "123,456",
        "Myanmar digits should work",
      );
      await input.fill("10,000");
      assert.equal(await input.inputValue(), "10,000");
      await input.press("Backspace");
      assert.equal(await input.inputValue(), "1,000");
      await input.fill("");
      assert.equal(await input.inputValue(), "", "Clearing is allowed");
    }
    async function closeModal() {
      await page.locator('#modal button[aria-label="Close"]').click();
    }

    const before = await readState();
    for (const entryType of [
      "cash_in",
      "cash_out",
      "expense",
      "funds_in",
      "funds_out",
    ]) {
      await page.evaluate((type) => window.entryForm(type), entryType);
      await verifyMoneyInput("#f_amount");
      if (["cash_in", "cash_out"].includes(entryType)) {
        await verifyMoneyInput("#f_fee");
        assert.equal(
          await page
            .locator("#f_customer")
            .evaluate((element) => element.required),
          true,
        );
      }
      await closeModal();
    }
    await page.evaluate(() => window.accountForm());
    await verifyMoneyInput("#f_opening");
    await closeModal();

    // The actual Channel import opens these fields through the same shared form.
    await page.evaluate(async () => {
      const { entryForm } = await import("/js/features/transactions.js");
      entryForm("cash_in", {
        receipt_format: "wave_channel",
        provider: "WavePay",
        account_kind: "Channel",
        amount: 30000,
        provider_commission: 9,
        provider_fee: 0,
        receipt_wallet_delta: -29991,
        previewUrl: "",

        transaction_type: "cash_in",
      });
    });
    await verifyMoneyInput("#f_provider_commission");
    await verifyMoneyInput("#f_provider_fee");
    await closeModal();
    await page.locator('.nav [data-nav="closing"]').first().click();
    await verifyMoneyInput('#closingform input[name="cash"]');
    await verifyMoneyInput('#closingform input[name="5"]');
    const after = await readState();
    assert.deepEqual(after.accounts, before.accounts);
    assert.deepEqual(after.entries, before.entries);
    assert.equal(after.cash, before.cash);

    // Verify normal submission still sends unformatted integer values.
    await page.evaluate(() => window.entryForm("funds_in"));
    await page.locator("#f_amount").fill("၁၀၀၀၀၀");
    await page.locator("#f_note").fill("Fictional opening cash");
    const posted = page.waitForResponse((response) =>
      response.url().endsWith("/api/entry"),
    );
    await page.locator("#save").click();
    assert.equal((await posted).status(), 200);
    assert.equal((await readState()).cash, 100000);
    assert.deepEqual(errors, []);
    console.log(
      "PASS: all money fields reject typed/pasted characters; Myanmar digits, commas, deletion, unchanged previews and posting work.",
    );
  } finally {
    await browser.close();
  }
}
main().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
