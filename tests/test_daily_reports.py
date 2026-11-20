"""Daily fee and closing reconciliation across reversals and business dates."""

import json
from unittest.mock import patch
from counter import clock
from tests.support import LedgerFixture


class DailyReportTests(LedgerFixture):
    def test_daily_totals_and_closing_across_two_days(self):
        # Remove fixture funding through its exact reversal, then seed known openings.
        self.req("reverse", id="cash", reason="Replace test opening")
        self.req("reverse", id="wallet", reason="Replace test opening")
        with patch.object(clock, "business_day", return_value="2026-11-19"):
            self.entry("open-cash", "funds_in", 300000)
            self.entry("open-k", "funds_in", 500000, 1)
            self.entry("open-w", "funds_in", 200000, 4)
            self.entry("k-in", "cash_in", 100000, 1)
            self.entry("k-out", "cash_out", 60000, 1, fee=400)
            self.entry("w-in", "cash_in", 50000, 4)
            self.entry("cash-expense", "expense", 2000)
            self.entry("wallet-expense", "expense", 1000, 4)
            self.req("reverse", id="k-out", reason="Wrong entry")
            self.entry("capital", "funds_in", 10000)
            first = self.req("state")[1]
            self.assertEqual(first["cash"], 458200)
            self.assertEqual(first["accounts"][0]["balance"], 400000)
            self.assertEqual(first["accounts"][3]["balance"], 149000)
            first_counts = self.counts()
            self.assertEqual(
                self.req("closing", counts=dict(first_counts, cash=458201))[0], 400
            )
            code, first = self.req(
                "closing", counts=first_counts, note="Day one matched"
            )
            self.assertEqual(code, 200)
            self.assertEqual(self.entry("closed-write", "expense", 1)[0], 400)
        with patch.object(clock, "business_day", return_value="2026-11-20"):
            self.entry(
                "second-out",
                "cash_out",
                100000,
                1,
                fee_mode="separate",
                fee_cash_received=500,
            )
            self.req("reverse", id="w-in", reason="Provider correction next day")
            self.entry("second-expense", "expense", 600)
            self.entry("withdraw-capital", "funds_out", 10000, 1)
            self.entry("add-wallet", "funds_in", 2000, 4)
            second = self.req("state")[1]
            self.assertEqual(second["cash"], 308000)
            self.assertEqual(second["accounts"][0]["balance"], 490000)
            self.assertEqual(second["accounts"][3]["balance"], 201000)
            originals = {entry["id"]: entry for entry in second["entries"]}
            included = [
                entry
                for entry in second["entries"]
                if not entry["reversed"]
                or any(row["reversal_of"] == entry["id"] for row in second["entries"])
            ]
            for date, fees, cash_in, cash_out, expenses in [
                ("2026-11-19", 200, 150000, 0, 3000),
                ("2026-11-20", 400, -50000, 100000, 600),
            ]:
                daily = [entry for entry in included if entry["business_date"] == date]
                self.assertEqual(sum(entry["fee"] for entry in daily), fees)

                def principal(kind):
                    return sum(
                        entry["amount"]
                        for entry in daily
                        if entry["type"] == kind
                        or (
                            entry["reversal_of"]
                            and originals[entry["reversal_of"]]["type"] == kind
                        )
                    )

                self.assertEqual(principal("cash_in"), cash_in)
                self.assertEqual(principal("cash_out"), cash_out)
                self.assertEqual(principal("expense"), expenses)
            second_counts = self.counts()
            self.assertEqual(
                self.req("closing", counts=dict(second_counts, cash=308001))[0], 400
            )
            code, result = self.req(
                "closing", counts=second_counts, note="Day two matched"
            )
            self.assertEqual(code, 200)
            snapshots = {
                row["business_date"]: json.loads(row["snapshot"])
                for row in result["closings"]
            }
            self.assertEqual(snapshots["2026-11-19"]["expected"], first_counts)
            self.assertEqual(snapshots["2026-11-20"]["expected"], second_counts)
            self.assertEqual(snapshots["2026-11-20"]["counted"], second_counts)
            self.assertEqual(self.entry("after-close", "expense", 1)[0], 400)
            code, report = self.req("reports/daily?date=2026-11-20")
            self.assertEqual(code, 200)
            self.assertEqual(report["totals"]["fees"], 400)
            self.assertEqual(report["totals"]["cash_in"], -50000)
            self.assertEqual(report["totals"]["cash_out"], 100000)
            self.assertEqual(report["totals"]["opening"], 549000)
            self.assertEqual(report["totals"]["closing"], 691000)
            code, wallet = self.req("reports/daily?date=2026-11-20&account_id=1")
            self.assertEqual(code, 200)
            self.assertEqual(len(wallet["accounts"]), 1)
            self.assertEqual(wallet["totals"]["opening"], 400000)
            self.assertEqual(wallet["totals"]["closing"], 490000)
            self.assertEqual(wallet["totals"]["fees"], 500)
            self.assertEqual(wallet["closing"]["counted"]["1"], 490000)
            self.assertEqual(
                self.req("reports/daily?date=2026-11-20&account_id=99999")[0], 400
            )
            self.assertEqual(self.req("reports/daily?date=bad")[0], 400)
            self.snapshot = result
