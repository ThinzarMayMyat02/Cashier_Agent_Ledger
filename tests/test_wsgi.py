"""The cloud transport must preserve sessions, origin checks and atomic postings."""

import io
import json
import os
import tempfile
import unittest
from unittest.mock import patch
from wsgiref.util import setup_testing_defaults
from wsgiref.validate import validator
from counter import database
from counter.wsgi import application


class WSGITests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        database.DB = os.path.join(self.directory.name, "ledger.sqlite3")
        database.initialize()
        self.cookie = ""
        self.environment = patch.dict(
            os.environ, {"LEDGER_ALLOWED_HOSTS": "test.local"}
        )
        self.environment.start()

    def tearDown(self):
        self.environment.stop()
        self.directory.cleanup()

    def request(self, path, data=None, method=None, scheme="https", headers=None):
        environ = {}
        setup_testing_defaults(environ)
        route, _, query = path.partition("?")
        body = json.dumps(data).encode() if data is not None else b""
        environ.update(
            PATH_INFO=route,
            QUERY_STRING=query,
            REQUEST_METHOD=method or ("POST" if data is not None else "GET"),
            CONTENT_TYPE="application/json",
            CONTENT_LENGTH=str(len(body)),
            HTTP_HOST="test.local",
            HTTP_COOKIE=self.cookie,
            **{"wsgi.input": io.BytesIO(body), "wsgi.url_scheme": scheme}
        )
        environ.update(headers or {})
        response = {}

        def start(status, response_headers, exc_info=None):
            response.update(
                status=int(status.split()[0]), headers=dict(response_headers)
            )

        iterator = validator(application)(environ, start)
        try:
            response["body"] = b"".join(iterator)
        finally:
            iterator.close()
        if "Set-Cookie" in response["headers"]:
            self.cookie = response["headers"]["Set-Cookie"].split(";")[0]
        return response

    def setup_owner(self):
        result = self.request(
            "/api/setup", {"name": "Cloud Test", "password": "fictional-password-123"}
        )
        self.assertEqual(result["status"], 200)
        return result

    def entry(self, identity, entry_type, amount, account_id=None, **extras):
        return self.request(
            "/api/entry",
            dict(
                id=identity,
                type=entry_type,
                amount=amount,
                account_id=account_id,
                customer="Test Customer",
                note="Fixture",
                **extras
            ),
        )

    def test_wsgi_contract_and_static_isolation(self):
        self.assertEqual(self.request("/")["status"], 200)
        for path in ("/ledger.sqlite3", "/Developer.md", "/../server.py"):
            self.assertEqual(self.request(path)["status"], 404)
        self.assertEqual(self.request("/", method="DELETE")["status"], 405)
        self.assertEqual(
            self.request("/", headers={"HTTP_HOST": "other.local"})["status"], 400
        )
        self.assertEqual(self.request("/api/state")["status"], 401)

    def test_secure_session_origin_and_json_validation(self):
        self.assertIn("Secure", self.setup_owner()["headers"]["Set-Cookie"])
        for data in ([], "text", None):
            self.assertEqual(
                self.request("/api/entry", data, method="POST")["status"], 400
            )
        result = self.request(
            "/api/entry",
            {"id": "bad"},
            headers={"HTTP_ORIGIN": "https://attacker.local"},
        )
        self.assertEqual(result["status"], 400)
        result = self.request(
            "/api/login",
            {"name": "Cloud Test", "password": "fictional-password-123"},
            scheme="http",
            headers={"HTTP_X_FORWARDED_PROTO": "https"},
        )
        self.assertNotIn("Secure", result["headers"]["Set-Cookie"])
        with patch.dict(os.environ, {"LEDGER_COOKIE_SECURE": "1"}):
            result = self.request(
                "/api/login",
                {"name": "Cloud Test", "password": "fictional-password-123"},
                scheme="http",
            )
        self.assertIn("Secure", result["headers"]["Set-Cookie"])

    def test_posting_and_private_import_share_the_existing_ledger(self):
        self.setup_owner()
        self.assertEqual(self.entry("cash", "funds_in", 1000000)["status"], 200)
        self.assertEqual(self.entry("wallet", "funds_in", 100000, 5)["status"], 200)
        before = json.loads(self.request("/api/state")["body"])
        extracted = dict(
            provider="WavePay",
            receipt_format="wave_channel",
            amount=30000,
            provider_commission=9,
            provider_fee=0,
            customer="",
            masked_phone="",
            warnings=[],
            text="Fixture",
        )
        with patch("counter.http.extract_image", return_value=(b"fixture", extracted)):
            draft = json.loads(
                self.request(
                    "/api/receipt/extract", {"provider": "WavePay", "image": "fixture"}
                )["body"]
            )
        self.assertEqual(
            json.loads(self.request("/api/state")["body"])["cash"], before["cash"]
        )
        extra = dict(
            receipt={
                key: draft[key]
                for key in ("provider", "receipt_format", "masked_phone")
                if key in draft
            },
            receipt_confirmed=True,
            provider_transaction_id="WSGI-RECEIPT-123",
            provider_commission=9,
            provider_fee=0,
        )
        self.assertEqual(
            self.entry("channel", "cash_in", 30000, 5, **extra)["status"], 200
        )
        after = json.loads(self.request("/api/state")["body"])
        self.assertEqual(after["cash"], 1030100)
        self.assertEqual(after["accounts"][4]["balance"], 70009)
        self.assertEqual(
            self.entry("duplicate", "cash_in", 30000, 5, **extra)["status"], 400
        )
        report = json.loads(
            self.request(
                "/api/reports/daily?date=" + after["business_date"] + "&account_id=5"
            )["body"]
        )
        self.assertEqual(report["totals"]["fees"], 100)
        self.assertEqual(report["totals"]["provider_commission"], 9)
        self.assertEqual(
            self.request(
                "/api/reverse", {"id": "channel", "reason": "Test correction"}
            )["status"],
            200,
        )
        state = json.loads(self.request("/api/state")["body"])
        self.assertEqual(state["cash"], before["cash"])
        self.assertEqual(state["accounts"], before["accounts"])
        counts = {
            "cash": state["cash"],
            **{str(account["id"]): account["balance"] for account in state["accounts"]},
        }
        self.assertEqual(
            self.request("/api/closing", {"counts": counts})["status"], 200
        )
        self.assertEqual(self.entry("closed", "cash_out", 1000, 5)["status"], 400)
