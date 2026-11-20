"""WavePay-specific parsing is separate from the verified KBZPay formats."""

import unittest
from counter.receipts.parser import parse_receipt


class WavePayOCRTests(unittest.TestCase):
    def receipt(self, heading, amount, time="06:12 PM"):
        return parse_receipt(
            {
                "lines": [
                    heading,
                    "SAMPLE CUSTOMER",
                    "(****9731)",
                    "1234567890 @",
                    "20 Nov 2026 •",
                    time,
                    amount + " Ks",
                    "0.00 Ks",
                    amount + " Ks",
                ]
            },
            "WavePay",
        )

    def test_send_and_receive(self):
        sent = self.receipt("Send Money", "-300000.00")
        self.assertEqual(sent["amount"], 300000)
        self.assertEqual(sent["transaction_type"], "cash_in")
        self.assertEqual(sent["customer"], "SAMPLE CUSTOMER")
        self.assertEqual(sent["masked_phone"], "****9731")
        self.assertEqual(sent["phone"], "")
        self.assertEqual(sent["provider_transaction_id"], "1234567890")
        self.assertEqual(sent["receipt_time"], "20/11/2026 18:12:00")
        received = self.receipt("Receive Money", "200400.00", "06:18 PM")
        self.assertEqual(received["amount"], 200400)
        self.assertEqual(received["transaction_type"], "cash_out")
        self.assertEqual(received["receipt_time"], "20/11/2026 18:18:00")

    def test_conflicting_sign_requires_manual_direction(self):
        self.assertEqual(
            self.receipt("Receive Money", "-200400.00")["transaction_type"], ""
        )

    def test_wave_header_is_required_for_unlabelled_fields(self):
        result = self.receipt("Unknown receipt", "300000.00")
        self.assertEqual(result["customer"], "")
        self.assertEqual(result["provider_transaction_id"], "")

    def test_provider_fee_is_separate_from_total(self):
        result = parse_receipt(
            {"lines": ["Send Money", "-100000.00 Ks", "500.00 Ks", "-100500.00 Ks"]},
            "WavePay",
        )
        self.assertEqual(result["amount"], 100500)
        self.assertEqual(result["provider_fee"], 500)
