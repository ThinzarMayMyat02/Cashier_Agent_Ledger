"""Closing history reads every saved record rather than the state preview."""

import json
from datetime import date, timedelta
from counter import database
from tests.support import LedgerFixture


class ClosingHistoryTests(LedgerFixture):
    def seed_history(self):
        with database.connect() as connection:
            for index in range(35):
                day = (date(2020, 1, 1) + timedelta(days=index)).isoformat()
                snapshot = json.dumps(
                    dict(
                        expected={"cash": 100 + index, "1": 200},
                        counted={"cash": 100 + index, "1": 200},
                        note=f"Closing {index}",
                    )
                )
                connection.execute(
                    "INSERT INTO closings(staff,snapshot,business_date) VALUES(1,?,?)",
                    (snapshot, day),
                )

    def test_old_date_outside_latest_thirty_is_accessible(self):
        self.seed_history()
        self.assertEqual(len(self.req("state")[1]["closings"]), 30)
        code, result = self.req("closings?date=2020-01-01")
        self.assertEqual(code, 200)
        self.assertEqual(result["total"], 1)
        saved = json.loads(result["records"][0]["snapshot"])
        self.assertEqual(saved["expected"]["cash"], 100)
        self.assertEqual(saved["note"], "Closing 0")
        self.assertEqual(self.req("closings?date=2010-01-01")[1]["total"], 0)

    def test_pagination_covers_all_records_and_rejects_bad_filters(self):
        self.seed_history()
        ids = []
        for page, expected in [(1, 10), (2, 10), (3, 10), (4, 5)]:
            code, result = self.req("closings?page=" + str(page))
            self.assertEqual(code, 200)
            self.assertEqual(result["total"], 35)
            self.assertEqual(len(result["records"]), expected)
            ids.extend(row["id"] for row in result["records"])
        self.assertEqual(len(set(ids)), 35)
        for query in ["date=2020-02-31", "page=0", "page=abc", "date=2020-01-01%27"]:
            self.assertEqual(self.req("closings?" + query)[0], 400)
        self.req("logout", ignored=True)
        self.assertEqual(self.req("closings")[0], 401)

    def test_legacy_timestamp_uses_myanmar_date_without_modifying_snapshot(self):
        before = self.counts()
        snapshot = json.dumps(
            dict(
                expected={"cash": 123}, counted={"cash": 120}, note="Legacy observation"
            )
        )
        with database.connect() as connection:
            connection.execute(
                "INSERT INTO closings(staff,snapshot,created) VALUES(1,?,'2020-01-01T20:00:00Z')",
                (snapshot,),
            )
        code, result = self.req("closings?date=2020-01-02")
        self.assertEqual(code, 200)
        self.assertEqual(result["records"][0]["closing_date"], "2020-01-02")
        self.assertEqual(result["records"][0]["snapshot"], snapshot)
        self.assertEqual(self.counts(), before)
