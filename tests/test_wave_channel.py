"""Channel principal, net wallet movement and commission stay distinct."""

from unittest.mock import patch
from counter.receipts.parser import parse_receipt
from counter import clock
from tests.support import LedgerFixture


def channel_receipt(incoming=False):
    return parse_receipt(
        {
            "lines": (
                [
                    "Receive Money",
                    "+600,000.00 Ks",
                    "0.00 Ks",
                    "1111111111",
                    "12/Sample(N)******",
                    "2222222222",
                    "19 Nov 2026 • 05:56 PM",
                    "600000.00 Ks",
                    "0.00 Ks",
                    "600000.00 Ks",
                ]
                if incoming
                else [
                    "Cash In",
                    "- 30,000.00 Ks",
                    "9.00 Ks",
                    "9770000000",
                    "3333333333 G",
                    "18 Nov 2026 • 05:50 PM",
                    "-30000.00 Ks",
                    "0.00 Ks",
                    "9.00 Ks",
                    "-29991.00 Ks",
                ]
            )
        },
        "WavePay",
    )


class WaveChannelTests(LedgerFixture):
    def draft(self, incoming=False):
        extracted = channel_receipt(incoming)
        before = self.counts()
        with patch("counter.http.extract_image", return_value=(b"fixture", extracted)):
            code, draft = self.req(
                "receipt/extract", provider="WavePay", image="fixture"
            )
        self.assertEqual(code, 200)
        self.assertEqual(self.counts(), before)
        return draft

    def payload(self, draft):
        return dict(
            customer="Test Customer",
            provider_transaction_id=draft["provider_transaction_id"],
            receipt_import_id=draft["import_id"],
            receipt_confirmed=True,
            provider_commission=draft["provider_commission"],
            provider_fee=draft["provider_fee"],
        )

    def test_channel_fields(self):
        sent = channel_receipt()
        self.assertEqual(sent["amount"], 30000)
        self.assertEqual(sent["total_amount"], 29991)
        self.assertEqual(sent["provider_commission"], 9)
        self.assertEqual(sent["receipt_wallet_delta"], -29991)
        self.assertEqual(sent["phone"], "9770000000")
        self.assertEqual(sent["provider_transaction_id"], "3333333333")
        self.assertEqual(sent["receipt_time"], "18/11/2026 17:50:00")
        received = channel_receipt(True)
        self.assertEqual(received["amount"], 600000)
        self.assertEqual(received["provider_transaction_id"], "2222222222")
        self.assertEqual(received["customer"], "")
        self.assertEqual(received["phone"], "")
        self.assertEqual(received["transaction_type"], "cash_out")

    def test_post_report_reverse_and_close(self):
        self.entry("channel-opening", "funds_in", 100000, 5)
        before = self.counts()
        draft = self.draft()
        payload = self.payload(draft)
        self.assertEqual(
            self.entry("wrong-kind", "cash_in", 30000, 4, **payload)[0], 400
        )
        self.assertEqual(self.counts(), before)
        code, state = self.entry("channel-in", "cash_in", 30000, 5, **payload)
        self.assertEqual(code, 200, state)
        self.assertEqual(self.counts()["cash"], before["cash"] + 30100)
        self.assertEqual(self.counts()["5"], before["5"] - 29991)
        row = next(e for e in state["entries"] if e["id"] == "channel-in")
        self.assertEqual(row["fee"], 100)
        self.assertEqual(row["provider_commission"], 9)
        received = self.draft(True)
        self.assertEqual(
            self.entry("channel-out", "cash_out", 600000, 5, **self.payload(received))[
                0
            ],
            200,
        )
        self.assertEqual(self.counts()["cash"], before["cash"] + 30100 - 597000)
        self.assertEqual(self.counts()["5"], before["5"] - 29991 + 600000)
        _, report = self.req(
            "reports/daily?date=" + clock.business_day() + "&account_id=5"
        )
        self.assertEqual(report["totals"]["cash_in"], 30000)
        self.assertEqual(report["totals"]["cash_out"], 600000)
        self.assertEqual(report["totals"]["fees"], 3100)
        self.assertEqual(report["totals"]["provider_commission"], 9)
        self.assertEqual(report["totals"]["closing"], self.counts()["5"])
        self.assertEqual(
            self.entry("duplicate", "cash_in", 30000, 5, **payload)[0], 400
        )
        self.assertEqual(
            self.req("reverse", id="channel-out", reason="Test reversal")[0], 200
        )
        self.assertEqual(
            self.req("reverse", id="channel-in", reason="Test reversal")[0], 200
        )
        self.assertEqual(self.counts(), before)
        _, report = self.req(
            "reports/daily?date=" + clock.business_day() + "&account_id=5"
        )
        for key in (
            "fees",
            "provider_commission",
            "provider_fee",
            "cash_in",
            "cash_out",
        ):
            self.assertEqual(report["totals"][key], 0)
        self.assertEqual(self.req("closing", counts=self.counts())[0], 200)

    def test_missing_customer_is_rejected_without_consuming_draft(self):
        draft = self.draft(True)
        payload = self.payload(draft)
        before = self.counts()
        for name in ("", "   ", "\t", None):
            payload["customer"] = name
            self.assertEqual(
                self.entry("missing-name", "cash_out", 600000, 5, **payload)[0], 400
            )
        self.assertEqual(self.counts(), before)
        payload["customer"] = "စမ်းသပ် ဖောက်သည်"
        self.assertEqual(
            self.entry("named-import", "cash_out", 600000, 5, **payload)[0], 200
        )
        for kind in ("cash_in", "cash_out"):
            self.assertEqual(
                self.entry("blank-manual", kind, 1000, 1, customer="")[0], 400
            )
            self.assertEqual(
                self.entry("valid-" + kind, kind, 1000, 1, customer="Test Customer")[0],
                200,
            )

    def test_adjustments_cannot_be_forged_for_manual_entry(self):
        self.assertEqual(
            self.entry("manual-commission", "cash_in", 1000, 5, provider_commission=9)[
                0
            ],
            400,
        )

    def test_provider_fee_and_commission_are_wallet_only_and_reversible(self):
        self.entry("opening", "funds_in", 100000, 5)
        before = self.counts()
        draft = self.draft()
        payload = self.payload(draft)
        payload["provider_fee"] = 5
        payload["provider_commission"] = -1
        self.assertEqual(self.entry("invalid", "cash_in", 30000, 5, **payload)[0], 400)
        self.assertEqual(self.counts(), before)
        payload["provider_commission"] = 9
        code, state = self.entry("adjusted", "cash_in", 30000, 5, fee=200, **payload)
        self.assertEqual(code, 200)
        self.assertEqual(self.counts()["cash"], before["cash"] + 30200)
        self.assertEqual(self.counts()["5"], before["5"] - 29996)
        row = next(e for e in state["entries"] if e["id"] == "adjusted")
        self.assertEqual(row["cash_delta"] + row["wallet_delta"], 200 + 9 - 5)
        _, report = self.req(
            "reports/daily?date=" + clock.business_day() + "&account_id=5"
        )
        self.assertEqual(report["totals"]["fees"], 200)
        self.assertEqual(report["totals"]["provider_commission"], 9)
        self.assertEqual(report["totals"]["provider_fee"], 5)
        self.assertEqual(
            self.req("reverse", id="adjusted", reason="Test correction")[0], 200
        )
        self.assertEqual(self.counts(), before)
        _, report = self.req(
            "reports/daily?date=" + clock.business_day() + "&account_id=5"
        )
        self.assertEqual(report["totals"]["provider_fee"], 0)

    def test_normal_wave_receipt_with_four_amount_rows_stays_normal(self):
        r = parse_receipt(
            {
                "lines": [
                    "Receive Money",
                    "+100000.00 Ks",
                    "1234567890",
                    "20 Nov 2026 • 06:18 PM",
                    "100000.00 Ks",
                    "0.00 Ks",
                    "100000.00 Ks",
                ]
            },
            "WavePay",
        )
        self.assertNotIn("receipt_format", r)
