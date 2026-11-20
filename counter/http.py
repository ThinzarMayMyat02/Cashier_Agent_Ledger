"""HTTP transport and route dispatch. Services own business validation."""

import json
import sqlite3
import traceback
from http.server import BaseHTTPRequestHandler
from urllib.parse import urlsplit, parse_qs

from . import auth, database
from .accounts import save_account
from .closing import close_day
from .config import PUBLIC_ROOT
from .ledger import post_entry
from .queries import get_shop_state
from .reports import daily_report
from .receipts.reader import extract_image
from .reversals import reverse_entry
from .team import create_staff

WRITE_ROUTES = {
    "/api/account": save_account,
    "/api/staff": create_staff,
    "/api/entry": post_entry,
    "/api/reverse": reverse_entry,
    "/api/closing": close_day,
}
CONTENT_TYPES = {
    ".html": "text/html; charset=utf-8",
    ".js": "text/javascript; charset=utf-8",
    ".css": "text/css; charset=utf-8",
}


class Handler(BaseHTTPRequestHandler):
    """Serve browser assets and preserve the existing JSON API contracts."""

    def send(self, data, status=200, cookie=None):
        body = json.dumps(data).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        if cookie:
            self.send_header("Set-Cookie", cookie)
        self.end_headers()
        self.wfile.write(body)

    def user(self, connection):
        return auth.current_user(connection, self.headers.get("Cookie"))

    def do_GET(self):
        if urlsplit(self.path).path == "/api/reports/daily":
            with database.connect() as connection:
                connection.execute("BEGIN")
                if not self.user(connection):
                    self.send({"error": "Please sign in"}, 401)
                    return
                query = parse_qs(urlsplit(self.path).query)
                try:
                    report = daily_report(
                        connection,
                        query.get("date", [""])[0],
                        query.get("account_id", [""])[0],
                    )
                    self.send(report)
                except ValueError as error:
                    self.send({"error": str(error)}, 400)
            return
        if self.path == "/api/state":
            with database.connect() as connection:
                user = self.user(connection)
                data = (
                    get_shop_state(connection, user)
                    if user
                    else {
                        "setup": not bool(
                            connection.execute("SELECT 1 FROM users").fetchone()
                        )
                    }
                )
                self.send(data, 200 if user else 401)
            return

        path = urlsplit(self.path).path
        relative_path = "index.html" if path == "/" else path.lstrip("/")
        asset = (PUBLIC_ROOT / relative_path).resolve()
        if (
            PUBLIC_ROOT not in asset.parents
            or asset.suffix not in CONTENT_TYPES
            or not asset.is_file()
        ):
            self.send({"error": "Not found"}, 404)
            return
        self.send_response(200)
        self.send_header("Content-Type", CONTENT_TYPES[asset.suffix])
        self.send_header("Cache-Control", "no-cache")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.end_headers()
        self.wfile.write(asset.read_bytes())

    def read_command(self):
        """Reject cross-origin browser writes and enforce endpoint body limits."""
        origin = self.headers.get("Origin")
        if origin and origin.split("://", 1)[-1] != self.headers.get("Host"):
            raise ValueError("Invalid request origin")
        size = int(self.headers.get("Content-Length", "0"))
        limit = 7500000 if self.path == "/api/receipt/extract" else 20000
        if not 0 < size <= limit:
            raise ValueError("Request too large")
        command = json.loads(self.rfile.read(size))
        if not isinstance(command, dict):
            raise ValueError("Send a JSON object")
        return command

    def do_POST(self):
        try:
            data = self.read_command()
            if self.path == "/api/receipt/extract":
                self.extract_receipt(data)
                return
            self.write_command(data)
        except (ValueError, TypeError, sqlite3.IntegrityError) as error:
            message = (
                "Duplicate name or transaction. Refresh and check history."
                if isinstance(error, sqlite3.IntegrityError)
                else str(error)
            )
            self.send({"error": message}, 400)
        except Exception:
            traceback.print_exc()
            self.send({"error": "Could not save. Please retry."}, 500)

    def extract_receipt(self, data):
        """Run slow OCR outside the serialized ledger transaction."""
        with database.connect() as connection:
            user = self.user(connection)
            if not user:
                self.send({"error": "Please sign in"}, 401)
                return
        _image, extracted = extract_image(data.get("image", ""), data.get("provider"))
        del _image
        data.pop("image", None)
        extracted.pop("text", None)
        with database.connect() as connection:
            current_user = self.user(connection)
            if not current_user or current_user["id"] != user["id"]:
                self.send({"error": "Please sign in"}, 401)
                return
        self.send(extracted)

    def write_command(self, data):
        """Keep role checks, posting and close atomic."""
        with database.connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            if self.path in ("/api/setup", "/api/login"):
                token = auth.sign_in(connection, data, setup=self.path == "/api/setup")
                connection.commit()
                cookie = (
                    "ledger_session="
                    + token
                    + "; HttpOnly; SameSite=Strict; Path=/; Max-Age=43200"
                )
                if self.headers.get("X-Forwarded-Proto") == "https":
                    cookie += "; Secure"
                self.send({"ok": True}, cookie=cookie)
                return

            user = self.user(connection)
            if not user:
                self.send({"error": "Please sign in"}, 401)
                return
            if self.path == "/api/logout":
                auth.sign_out(connection, user)
                connection.commit()
                self.send({"ok": True}, cookie="ledger_session=; Path=/; Max-Age=0")
                return
            service = WRITE_ROUTES.get(self.path)
            if service is None:
                self.send({"error": "Not found"}, 404)
                return
            service(connection, user, data)
            connection.commit()
            self.send(get_shop_state(connection, user))
