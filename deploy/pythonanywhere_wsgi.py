"""Paste into the WSGI configuration file linked on PythonAnywhere's Web tab."""

import os
import sys
from pathlib import Path

# Replace YOUR_USERNAME. Keep the database outside the Git checkout.
account_home = Path("/home/YOUR_USERNAME")
project_path = account_home / "Cashier_Agent_Ledger"
data_path = account_home / "counter-data"
data_path.mkdir(mode=0o700, exist_ok=True)

sys.path.insert(0, str(project_path))
os.environ["LEDGER_DB"] = str(data_path / "ledger.sqlite3")
os.environ["LEDGER_ALLOWED_HOSTS"] = "YOUR_USERNAME.pythonanywhere.com"
os.environ["LEDGER_OCR_BACKEND"] = "tesseract"
os.environ["LEDGER_TESSERACT_CMD"] = "/usr/bin/tesseract"
os.environ["LEDGER_COOKIE_SECURE"] = "1"
os.environ["OMP_THREAD_LIMIT"] = "1"

from wsgi import application  # noqa: E402,F401
