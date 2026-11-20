"""Variance closes retain observed counts without adjusting the financial ledger."""

import json
from counter import clock
from tests.support import LedgerFixture


class ClosingModeTests(LedgerFixture):
    def test_strict_default_rejects_differences_even_with_note(self):
        counts = self.counts()
        wrong = dict(counts, cash=counts["cash"] - 100)
        self.assertEqual(self.req("closing", counts=wrong, note="Difference")[0], 400)
        self.assertEqual(self.counts(), counts)
        self.assertEqual(self.req("state")[1]["closings"], [])

    def test_variance_requires_note_then_saves_exact_counts_and_locks_day(self):
        before = self.counts()
        counts = dict(before, cash=before["cash"] - 100)
        counts["1"] += 200
        for note in ["", "   ", None, "x" * 501]:
            self.assertEqual(
                self.req(
                    "closing", counts=counts, closing_mode="allow_variance", note=note
                )[0],
                400,
            )
        code, state = self.req(
            "closing",
            counts=counts,
            closing_mode="allow_variance",
            note="  Cash short; wallet count checked  ",
        )
        self.assertEqual(code, 200)
        saved = json.loads(state["closings"][0]["snapshot"])
        self.assertEqual(saved["status"], "variance")
        self.assertEqual(saved["closing_mode"], "allow_variance")
        self.assertEqual(saved["expected"], before)
        self.assertEqual(saved["counted"], counts)
        self.assertEqual(saved["differences"]["cash"], -100)
        self.assertEqual(saved["differences"]["1"], 200)
        self.assertEqual(saved["note"], "Cash short; wallet count checked")
        self.assertEqual(self.counts(), before)
        report = self.req("reports/daily?date=" + clock.business_day())[1]
        self.assertEqual(report["closing"]["status"], "variance")
        self.assertEqual(report["closing"]["counted"], counts)
        self.assertEqual(self.entry("after-close", "expense", 100)[0], 400)
        self.assertEqual(
            self.req(
                "closing",
                counts=counts,
                closing_mode="allow_variance",
                note="Duplicate",
            )[0],
            400,
        )

    def test_allow_mode_with_matching_counts_is_marked_matched(self):
        counts = self.counts()
        self.assertEqual(
            self.req("closing", counts=counts, closing_mode="unknown")[0], 400
        )
        self.assertEqual(
            self.req(
                "closing",
                counts=dict(counts, cash=-1),
                closing_mode="allow_variance",
                note="Invalid",
            )[0],
            400,
        )
        code, state = self.req("closing", counts=counts, closing_mode="allow_variance")
        self.assertEqual(code, 200)
        saved = json.loads(state["closings"][0]["snapshot"])
        self.assertEqual(saved["status"], "matched")
        self.assertTrue(all(value == 0 for value in saved["differences"].values()))
