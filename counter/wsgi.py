"""WSGI transport adapter sharing the local server's routes and posting services."""

import io
import os
from email.message import Message
from http import HTTPStatus
from .http import Handler


class WSGIRequest(Handler):
    """Supply request/response streams without opening an HTTP server or socket."""

    def __init__(self, environ):
        self.path = environ.get("PATH_INFO", "/")
        if environ.get("QUERY_STRING"):
            self.path += "?" + environ["QUERY_STRING"]
        self.command = environ.get("REQUEST_METHOD", "GET").upper()
        self.headers = Message()
        for name, value in environ.items():
            if name.startswith("HTTP_"):
                self.headers[name[5:].replace("_", "-")] = str(value)
        for name in ("CONTENT_TYPE", "CONTENT_LENGTH"):
            if name in environ:
                self.headers[name.replace("_", "-")] = str(environ[name])
        # The WSGI server owns this scheme. Do not trust a caller's forwarded header.
        if "X-FORWARDED-PROTO" in self.headers:
            del self.headers["X-FORWARDED-PROTO"]
        self.headers["X-Forwarded-Proto"] = (
            "https"
            if os.environ.get("LEDGER_COOKIE_SECURE") == "1"
            else environ.get("wsgi.url_scheme", "http")
        )
        if not self.headers.get("Host"):
            self.headers["Host"] = environ.get("SERVER_NAME", "localhost")
        self.rfile = environ["wsgi.input"]
        self.wfile = io.BytesIO()
        self.status_code = 200
        self.response_headers = []

    def send_response(self, code, message=None):
        self.status_code = code

    def send_header(self, keyword, value):
        self.response_headers.append((keyword, str(value)))

    def end_headers(self):
        pass


def application(environ, start_response):
    request = WSGIRequest(environ)
    allowed_hosts = {
        host.strip().lower()
        for host in os.environ.get("LEDGER_ALLOWED_HOSTS", "").split(",")
        if host.strip()
    }
    if allowed_hosts and request.headers["Host"].lower() not in allowed_hosts:
        request.send({"error": "Invalid request host"}, 400)
    elif request.command == "GET":
        request.do_GET()
    elif request.command == "POST":
        request.do_POST()
    else:
        request.send({"error": "Method not allowed"}, 405)
        request.send_header("Allow", "GET, POST")
    body = request.wfile.getvalue()
    request.response_headers.append(("Content-Length", str(len(body))))
    start_response(
        f"{request.status_code} {HTTPStatus(request.status_code).phrase}",
        request.response_headers,
    )
    return [body]
