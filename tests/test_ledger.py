import unittest
import tempfile
import threading
import json
import urllib.request
import urllib.error
import http.cookiejar
import os
from counter import database, clock, http as http_api
from counter.fees import calculate_fee
from http.server import ThreadingHTTPServer


class LedgerTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        database.DB = os.path.join(cls.tmp.name, "test.sqlite3")
        database.initialize()
        cls.http = ThreadingHTTPServer(("127.0.0.1", 0), http_api.Handler)
        threading.Thread(target=cls.http.serve_forever, daemon=True).start()
        cls.url = "http://127.0.0.1:" + str(cls.http.server_port)

    @classmethod
    def tearDownClass(cls):
        cls.http.shutdown()
        cls.http.server_close()
        cls.tmp.cleanup()

    def test_ledger(self):
        owner = urllib.request.build_opener(
            urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar())
        )
        staff = urllib.request.build_opener(
            urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar())
        )

        def req(client, path, data=None):
            r = urllib.request.Request(
                self.url + "/api/" + path,
                data=json.dumps(data).encode() if data is not None else None,
                headers={"Content-Type": "application/json"},
            )
            try:
                with client.open(r) as res:
                    return res.status, json.load(res)
            except urllib.error.HTTPError as e:
                return e.code, json.load(e)

        self.assertEqual(req(owner, "state")[1]["setup"], True)
        self.assertEqual(
            req(owner, "setup", {"name": "Owner", "password": "longpassword123"})[0],
            200,
        )
        self.assertEqual(
            req(owner, "setup", {"name": "Other", "password": "longpassword123"})[0],
            400,
        )

        def entry(id, type, amount, aid=None, **kw):
            kw.setdefault("customer", "Test Customer")
            return req(
                owner,
                "entry",
                dict(
                    id=id,
                    type=type,
                    amount=amount,
                    account_id=aid,
                    note="test",
                    phone="0912345678",
                    **kw
                ),
            )

        s = req(owner, "state")[1]
        self.assertEqual(len(s["accounts"]), 5)
        aid = s["accounts"][0]["id"]
        self.assertEqual(entry("low", "cash_in", 150000, aid)[0], 400)
        self.assertEqual(entry("cash", "funds_in", 1000000)[1]["cash"], 1000000)
        entry("wallet", "funds_in", 2000000, aid)
        status, s = entry("in", "cash_in", 150000, aid)
        self.assertEqual(status, 200)
        self.assertEqual(s["cash"], 1150200)
        self.assertEqual(s["accounts"][0]["balance"], 1850000)
        self.assertEqual(s["entries"][0]["fee"], 200)
        status, s = entry("out", "cash_out", 150000, aid)
        self.assertEqual(s["cash"], 1000700)
        self.assertEqual(s["accounts"][0]["balance"], 2000000)
        self.assertEqual(s["entries"][0]["fee"], 500)
        self.assertEqual(entry("out", "cash_out", 150000, aid)[0], 400)
        s = entry("expense", "expense", 1000)[1]
        self.assertEqual(s["cash"], 999700)
        s = entry("wallet-expense", "expense", 2000, aid)[1]
        self.assertEqual(s["accounts"][0]["balance"], 1998000)
        s = req(owner, "reverse", {"id": "expense", "reason": "Wrong entry"})[1]
        self.assertEqual(s["cash"], 1000700)
        self.assertEqual(
            req(owner, "reverse", {"id": "expense", "reason": "Again"})[0], 400
        )
        self.assertEqual(
            req(owner, "staff", {"name": "Staff", "password": "staffpassword123"})[0],
            200,
        )
        self.assertEqual(
            req(staff, "login", {"name": "Staff", "password": "staffpassword123"})[0],
            200,
        )
        self.assertEqual(
            req(staff, "account", {"name": "Bad", "provider": "Bad", "kind": "Bad"})[0],
            400,
        )
        self.assertEqual(
            req(
                staff,
                "entry",
                dict(id="staff-fund", type="funds_in", amount=100, note="bad"),
            )[0],
            400,
        )
        self.assertEqual(req(staff, "reverse", {"id": "in", "reason": "bad"})[0], 400)
        status, s = req(
            staff,
            "entry",
            dict(id="staff-expense", type="expense", amount=100, note="Internet"),
        )
        self.assertEqual(status, 200)
        self.assertEqual(s["entries"][0]["staff_name"], "Staff")
        status, s = req(
            owner,
            "account",
            dict(
                name="Custom wallet",
                provider="Other",
                kind="Custom",
                opening=500,
                phone="09",
            ),
        )
        self.assertEqual(status, 200)
        custom = s["accounts"][-1]
        status, s = req(
            owner,
            "account",
            dict(
                id=custom["id"],
                name="Renamed",
                provider="Other",
                kind="New Type",
                active=True,
            ),
        )
        self.assertEqual(status, 200)
        self.assertEqual(s["accounts"][-1]["balance"], 500)
        self.assertEqual(entry("available", "expense", 10, custom["id"])[0], 200)
        s = req(owner, "state")[1]
        counts = {
            "cash": s["cash"],
            **{str(a["id"]): a["balance"] for a in s["accounts"]},
        }
        status, s = req(owner, "closing", dict(counts=counts, note="Matched"))
        self.assertEqual(status, 200)
        self.assertEqual(len(s["closings"]), 1)
        self.assertEqual(req(owner, "closing", dict(counts={}))[0], 400)
        self.assertEqual(req(owner, "logout", {})[0], 200)
        self.assertEqual(req(owner, "state")[0], 401)

    def test_fees(self):
        for a, fi, fo in [
            (100000, 100, 500),
            (120000, 200, 500),
            (150000, 200, 500),
            (1000000, 1000, 5000),
            (1100000, 1100, 5500),
            (1, 100, 100),
        ]:
            self.assertEqual(calculate_fee("cash_in", a), fi)
            self.assertEqual(calculate_fee("cash_out", a), fo)


if __name__ == "__main__":
    unittest.main()
