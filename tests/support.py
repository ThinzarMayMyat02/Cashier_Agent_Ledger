"""Isolated HTTP test fixture. Every case uses a temporary SQLite database."""

import http.cookiejar
import json
import os
import tempfile
import threading
import unittest
import urllib.error
import urllib.request
from http.server import ThreadingHTTPServer
from counter import database, http as http_api


class LedgerFixture(unittest.TestCase):

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        database.DB = os.path.join(self.tmp.name, "ledger.sqlite")
        database.initialize()
        self.http = ThreadingHTTPServer(("127.0.0.1", 0), http_api.Handler)
        threading.Thread(target=self.http.serve_forever, daemon=True).start()
        self.client = urllib.request.build_opener(
            urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar())
        )
        self.req("setup", name="Owner", password="testing-password-123")
        self.entry("cash", "funds_in", 10000000)
        self.entry("wallet", "funds_in", 10000000, 1)

    def tearDown(self):
        self.http.shutdown()
        self.http.server_close()
        self.tmp.cleanup()

    def req(self, path, **data):
        request = urllib.request.Request(
            "http://127.0.0.1:" + str(self.http.server_port) + "/api/" + path,
            data=json.dumps(data).encode() if data else None,
            headers={"Content-Type": "application/json"},
        )
        try:
            with self.client.open(request) as r:
                return (r.status, json.load(r))
        except urllib.error.HTTPError as e:
            return (e.code, json.load(e))

    def entry(self, id, type, amount, aid=None, **extras):
        extras.setdefault("customer", "Test Customer")
        return self.req(
            "entry",
            id=id,
            type=type,
            amount=amount,
            account_id=aid,
            note="fixture",
            phone="09",
            **extras
        )

    def counts(self):
        s = self.req("state")[1]
        return {
            "cash": s["cash"],
            **{str(a["id"]): a["balance"] for a in s["accounts"]},
        }
