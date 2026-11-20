import base64
import json
from unittest.mock import patch
from tests.support import LedgerFixture
from receipts import parse_receipt


class ReceiptTests(LedgerFixture):
    def test_parser(self):
        payload = (
            "KPRSC."
            + base64.urlsafe_b64encode(
                json.dumps({"tid": "00001234567890123456"}).encode()
            )
            .decode()
            .rstrip("=")
            + ".unverified"
        )
        result = parse_receipt(
            {
                "lines": [
                    "Payment Successful",
                    "−300,000.00 (Ks)",
                    "26/09/2026 17:53:25",
                    "Amount",
                    "−300,000.00 Ks",
                ],
                "qr": [payload],
            },
            "KBZPay",
        )
        self.assertEqual(result["provider_transaction_id"], "00001234567890123456")
        self.assertEqual(result["amount"], 300000)
        self.assertEqual(result["receipt_time"], "26/09/2026 17:53:25")
        self.assertEqual(
            parse_receipt(
                {
                    "lines": [
                        "Wave Money",
                        "Transaction ID: WAVE-123456",
                        "50,000 MMK",
                    ],
                    "qr": [],
                },
                "WavePay",
            )["provider_transaction_id"],
            "WAVE-123456",
        )
        self.assertIsNone(
            parse_receipt({"lines": ["10,000 Ks", "20,000 Ks"]}, "WavePay")["amount"]
        )

    def test_total_and_signed_customer_details(self):
        result = parse_receipt(
            {
                "lines": [
                    "98,700.00 Ks",
                    "Amount:",
                    "98,600.00 Ks",
                    "Fees:",
                    "100.00 Ks",
                    "Total Amount:",
                    "98,700.00 Ks",
                    "Customer Name:",
                    "Ledger No:",
                    "30/38/02",
                ]
            },
            "KBZPay",
        )
        self.assertEqual(result["amount"], 98700)
        self.assertEqual(result["customer"], "")
        self.assertEqual(result["transaction_type"], "")
        for sign, kind in [("+", "cash_out"), ("−", "cash_in")]:
            result = parse_receipt(
                {
                    "lines": [
                        sign + "32,900.00 Ks",
                        "Transfer From",
                        "TEST CUSTOMER",
                        "(******6082)",
                    ]
                },
                "KBZPay",
            )
            self.assertEqual(result["transaction_type"], kind)
            self.assertEqual(result["customer"], "TEST CUSTOMER")
            self.assertEqual(result["phone"], "")
            self.assertEqual(result["masked_phone"], "******6082")

    def test_kbz_myanmar_layout_without_readable_labels(self):
        result = parse_receipt(
            {
                "lines": [
                    "+200,000.00 (Ks)",
                    "16/11/2026 12:53:35",
                    "01004337040139828414",
                    "U SAMPLE CUSTOMER",
                    "(******4898)",
                ]
            },
            "KBZPay",
        )
        self.assertEqual(result["customer"], "U SAMPLE CUSTOMER")
        self.assertEqual(result["masked_phone"], "******4898")
        self.assertEqual(result["phone"], "")
        self.assertEqual(result["provider_transaction_id"], "01004337040139828414")
        self.assertEqual(result["transaction_type"], "cash_out")
        wave = parse_receipt(
            {"lines": ["U SAMPLE CUSTOMER", "(******4898)", "01004337040139828414"]},
            "WavePay",
        )
        self.assertEqual(wave["customer"], "")
        self.assertEqual(wave["provider_transaction_id"], "")

    def test_imported_masked_phone_is_persisted(self):
        extracted = dict(
            provider="KBZPay",
            provider_transaction_id="MASKED-TEST-123",
            amount=200000,
            receipt_time="",
            masked_phone="******4898",
            customer="U SAMPLE CUSTOMER",
            warnings=[],
            text="",
        )
        with patch("counter.http.extract_image", return_value=(b"fixture", extracted)):
            _, draft = self.req("receipt/extract", provider="KBZPay", image="fixture")
        code, state = self.entry(
            "masked-phone-import",
            "cash_out",
            200000,
            1,
            customer=extracted["customer"],
            receipt={
                key: draft[key]
                for key in ("provider", "receipt_format", "masked_phone")
                if key in draft
            },
            receipt_confirmed=True,
        )
        self.assertEqual(code, 200)
        entry = next(
            row for row in state["entries"] if row["id"] == "masked-phone-import"
        )
        self.assertEqual(entry["customer_phone_masked"], "******4898")
        self.assertEqual(entry["customer"], "U SAMPLE CUSTOMER")

    def test_optional_id_and_duplicates(self):
        self.assertEqual(self.entry("no-id", "cash_in", 100000, 1)[0], 200)
        self.assertEqual(
            self.entry(
                "with-id", "cash_in", 100000, 1, provider_transaction_id="00123456"
            )[0],
            200,
        )
        before = self.counts()
        self.assertEqual(
            self.entry(
                "duplicate", "cash_out", 100000, 1, provider_transaction_id="00123456"
            )[0],
            400,
        )
        self.assertEqual(self.counts(), before)
        entry = next(e for e in self.req("state")[1]["entries"] if e["id"] == "with-id")
        self.assertEqual(entry["provider_transaction_id"], "00123456")

    def test_import_requires_review_and_posts_once(self):
        extracted = dict(
            provider="KBZPay",
            provider_transaction_id="012345678900",
            amount=300000,
            receipt_time="26/09/2026 17:53:25",
            warnings=[],
            text="fixture",
        )
        before = self.counts()
        with patch(
            "counter.http.extract_image", return_value=(b"fictional-image", extracted)
        ):
            code, draft = self.req(
                "receipt/extract", provider="KBZPay", image="fixture"
            )
        self.assertEqual(code, 200)
        self.assertEqual(self.counts(), before)
        extras = dict(
            provider_transaction_id=extracted["provider_transaction_id"],
            receipt={
                key: draft[key]
                for key in ("provider", "receipt_format", "masked_phone")
                if key in draft
            },
            receipt_time=extracted["receipt_time"],
        )
        self.assertEqual(
            self.entry("unconfirmed", "cash_in", 300000, 1, **extras)[0], 400
        )
        code, s = self.entry(
            "confirmed", "cash_in", 300000, 1, receipt_confirmed=True, **extras
        )
        self.assertEqual(code, 200)
        self.assertEqual(s["cash"], before["cash"] + 300300)
        self.assertEqual(
            self.entry(
                "reused", "cash_in", 300000, 1, receipt_confirmed=True, **extras
            )[0],
            400,
        )

    def test_provider_mismatch(self):
        extracted = dict(
            provider="WavePay",
            provider_transaction_id="",
            amount=50000,
            receipt_time="",
            warnings=[],
            text="",
        )
        with patch("counter.http.extract_image", return_value=(b"fixture", extracted)):
            _, draft = self.req("receipt/extract", provider="WavePay", image="fixture")
        self.assertEqual(
            self.entry(
                "wrong",
                "cash_out",
                50000,
                1,
                receipt={
                    key: draft[key]
                    for key in ("provider", "receipt_format", "masked_phone")
                    if key in draft
                },
                receipt_confirmed=True,
            )[0],
            400,
        )


if __name__ == "__main__":
    import unittest

    unittest.main()
