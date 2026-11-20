"""Accounting regression tests through the actual HTTP endpoints."""

import concurrent.futures
import json
import unittest
from unittest.mock import patch
from counter import database, clock
from counter.fees import calculate_fee
from tests.support import LedgerFixture


class Accounting(LedgerFixture):

    def test_customer_transactions_validate_the_outgoing_asset(self):
        before = self.counts()
        self.assertEqual(self.entry("too-large-in", "cash_in", 20000000, 1)[0], 400)
        self.assertEqual(self.entry("too-large-out", "cash_out", 20000000, 1)[0], 400)
        self.assertEqual(self.counts(), before)
        status, state = self.entry("deposit", "cash_in", 100000, 1)
        self.assertEqual(status, 200)
        self.assertEqual(state["cash"], 10100100)
        self.assertEqual(state["accounts"][0]["balance"], 9900000)
        status, state = self.entry("withdrawal", "cash_out", 100000, 1)
        self.assertEqual(status, 200)
        self.assertEqual(state["cash"], 10000600)
        self.assertEqual(state["accounts"][0]["balance"], 10000000)
        self.assertTrue(
            all(account["balance"] == 0 for account in state["accounts"][1:])
        )

    def test_fee_boundaries(self):
        for amount, expected in [
            (1, 100),
            (10000, 100),
            (10001, 300),
            (50000, 300),
            (50001, 500),
            (99999, 500),
            (100000, 500),
            (100001, 500),
            (199999, 500),
            (200000, 1000),
            (1000000, 5000),
            (1999999, 9500),
            (2000000, 8000),
            (2000125, 8001),
        ]:
            self.assertEqual(calculate_fee("cash_out", amount), expected)
        for amount, expected in [
            (100000, 100),
            (100001, 200),
            (1000000, 1000),
            (1000001, 1100),
        ]:
            self.assertEqual(calculate_fee("cash_in", amount), expected)

    def test_overrides_and_modes(self):
        (code, s) = self.entry(
            "in", "cash_in", 100000, 1, fee=50, override_reason="Discount"
        )
        self.assertEqual(code, 200)
        self.assertEqual(s["cash"], 10100050)
        self.assertEqual(s["entries"][0]["fee"], 50)
        self.assertEqual(s["entries"][0]["suggested_fee"], 100)
        (code, s) = self.entry(
            "deduct", "cash_out", 100000, 1, fee=400, override_reason="Discount"
        )
        self.assertEqual(code, 200)
        self.assertEqual(s["cash"], 10000450)
        (code, s) = self.entry(
            "separate",
            "cash_out",
            100000,
            1,
            fee=500,
            fee_mode="separate",
            fee_cash_received=500,
            cash_amount=100000,
        )
        self.assertEqual(code, 200)
        self.assertEqual(s["cash"], 9900950)
        self.assertEqual(s["accounts"][0]["balance"], 10100000)
        self.assertEqual(self.entry("bad", "cash_in", 100000, 1, fee=100001)[0], 400)
        self.assertEqual(
            self.entry("bad2", "cash_in", 100000, 1, fee=100, cash_amount=100050)[0],
            400,
        )
        self.assertEqual(
            self.entry("bad3", "cash_out", 100000, 1, fee_mode="separate")[0], 400
        )

    def test_fee_override_reason_is_optional(self):
        status, snapshot = self.entry("optional-reason", "cash_in", 100000, 1, fee=50)
        self.assertEqual(status, 200)
        entry = next(
            row for row in snapshot["entries"] if row["id"] == "optional-reason"
        )
        self.assertEqual(entry["fee"], 50)
        self.assertEqual(entry["override_reason"], "")

    def test_whole_amounts_and_rollback(self):
        before = self.counts()
        for bad in [True, 1.5, -1, 0, "1.5", 100000000001]:
            self.assertEqual(self.entry("bad", "expense", bad)[0], 400)
        self.assertEqual(self.entry("low", "cash_in", 20000000, 1)[0], 400)
        self.assertEqual(self.counts(), before)

    def test_reversal_is_dated_and_immutable_movements(self):
        with patch.object(clock, "business_day", return_value="2026-11-20"):
            self.entry("old", "cash_in", 100000, 1, fee=50, override_reason="Discount")
        with patch.object(clock, "business_day", return_value="2026-11-21"):
            (code, s) = self.req("reverse", id="old", reason="Mistake")
        self.assertEqual(code, 200)
        original = next((e for e in s["entries"] if e["id"] == "old"))
        reversal = next((e for e in s["entries"] if e["reversal_of"] == "old"))
        self.assertEqual(original["business_date"], "2026-11-20")
        self.assertEqual(reversal["business_date"], "2026-11-21")
        self.assertEqual(reversal["cash_delta"], -100050)
        self.assertEqual(reversal["fee"], -50)
        self.assertEqual(s["cash"], 10000000)
        self.assertEqual(self.req("reverse", id="old", reason="Again")[0], 400)
        self.assertEqual(self.req("reverse", id=reversal["id"], reason="Again")[0], 400)

    def test_close_blocks_writes_and_uses_myanmar_date(self):
        counts = self.counts()
        bad = dict(counts, cash=counts["cash"] + 1)
        self.assertEqual(self.req("closing", counts=bad)[0], 400)
        self.assertEqual(self.req("closing", counts=counts)[0], 200)
        self.assertEqual(self.entry("after", "expense", 1)[0], 400)
        self.assertEqual(self.req("reverse", id="cash", reason="after")[0], 400)
        self.assertEqual(
            self.req("account", name="X", provider="X", kind="X", opening=0)[0], 400
        )
        self.assertEqual(self.req("closing", counts=counts)[0], 400)
        self.assertEqual(clock.business_day("2026-11-20T18:00:00Z"), "2026-11-21")

    def test_serialized_balance_and_duplicate(self):

        def withdraw(i):
            return self.entry("race" + str(i), "funds_out", 7000000)[0]

        with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
            self.assertEqual(sorted(pool.map(withdraw, [1, 2])), [200, 400])
        self.assertEqual(self.req("state")[1]["cash"], 3000000)

        def duplicate(i):
            return self.entry("same", "expense", 100)[0]

        with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
            self.assertEqual(sorted(pool.map(duplicate, [1, 2])), [200, 400])
        self.assertEqual(self.req("state")[1]["cash"], 2999900)

    def test_close_and_post_race(self):
        counts = self.counts()

        def action(i):
            return (
                self.req("closing", counts=counts)[0]
                if i == 0
                else self.entry("racing-expense", "expense", 100)[0]
            )

        with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(action, [0, 1]))
        self.assertEqual(sorted(results), [200, 400])
        with database.connect() as c:
            closed = c.execute(
                "SELECT snapshot FROM closings WHERE business_date IS NOT NULL"
            ).fetchone()
        if closed:
            self.assertEqual(json.loads(closed["snapshot"])["expected"], self.counts())

    def test_new_opening_is_ledger_entry(self):
        (code, s) = self.req(
            "account", name="New", provider="Other", kind="Other", opening=500
        )
        self.assertEqual(code, 200)
        new = s["accounts"][-1]
        self.assertEqual(new["opening"], 0)
        self.assertEqual(new["balance"], 500)
        self.assertTrue(
            any(
                (
                    e["account_id"] == new["id"] and e["type"] == "funds_in"
                    for e in s["entries"]
                )
            )
        )
        self.assertEqual(
            self.req(
                "account",
                id=new["id"],
                name="New",
                provider="Other",
                kind="Other",
                active=False,
            )[0],
            400,
        )

    def test_migration_preserves_legacy_movements(self):
        with database.connect() as c:
            c.execute(
                "INSERT INTO entries(id,type,account_id,amount,fee,cash_delta,wallet_delta,staff) VALUES('legacy','cash_in',1,100000,100,100050,-100000,1)"
            )
            c.execute(
                "INSERT INTO entries(id,type,account_id,amount,fee,cash_delta,wallet_delta,staff,reversed) VALUES('legacy-reversed','cash_in',1,100000,100,100100,-100000,1,1)"
            )
        before = self.counts()
        database.initialize()
        database.initialize()
        self.assertEqual(self.counts(), before)
        legacy = next(
            (e for e in self.req("state")[1]["entries"] if e["id"] == "legacy")
        )
        self.assertEqual(legacy["recorded_fee"], 100)
        self.assertEqual(legacy["fee"], 50)
