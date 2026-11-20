"""Counter local server entry point. Run with python3 -B server.py."""

import os
from http.server import ThreadingHTTPServer

from counter.database import initialize
from counter.http import Handler


def main():
    initialize()
    host = os.environ.get("HOST", "127.0.0.1")
    port = int(os.environ.get("PORT", "8000"))
    print(f"Agent Ledger running at http://{host}:{port}", flush=True)
    ThreadingHTTPServer((host, port), Handler).serve_forever()


if __name__ == "__main__":
    main()
