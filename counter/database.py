"""SQLite connections and additive startup migrations for existing ledgers."""

import os
import sqlite3
from pathlib import Path
from .config import PROJECT_ROOT
from . import clock

DB = os.environ.get("LEDGER_DB", str(PROJECT_ROOT / "ledger.sqlite3"))


def connect():
    connection = sqlite3.connect(DB, timeout=20)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys=ON")
    return connection


def initialize():
    with connect() as connection:
        connection.executescript((Path(__file__).with_name("schema.sql")).read_text())
        columns = {
            row["name"] for row in connection.execute("PRAGMA table_info(entries)")
        }
        for name, definition in [
            ("suggested_fee", "INTEGER"),
            ("fee_mode", "TEXT"),
            ("override_reason", "TEXT"),
            ("reversal_of", "TEXT REFERENCES entries(id)"),
            ("collected_fee", "INTEGER"),
            ("business_date", "TEXT"),
            ("provider_transaction_id", "TEXT"),
            ("receipt_import_id", "TEXT"),
            ("receipt_time", "TEXT"),
            ("accounting_rule", "TEXT"),
            ("customer_phone_masked", "TEXT"),
            ("provider_commission", "INTEGER NOT NULL DEFAULT 0"),
            ("provider_fee", "INTEGER NOT NULL DEFAULT 0"),
            ("receipt_format", "TEXT"),
        ]:
            if name not in columns:
                connection.execute(
                    "ALTER TABLE entries ADD COLUMN " + name + " " + definition
                )
        connection.execute(
            "CREATE UNIQUE INDEX IF NOT EXISTS one_reversal ON entries(reversal_of) WHERE reversal_of IS NOT NULL"
        )
        connection.execute(
            "CREATE UNIQUE INDEX IF NOT EXISTS provider_receipt ON entries(account_id,provider_transaction_id) WHERE provider_transaction_id IS NOT NULL AND provider_transaction_id<>'' AND reversal_of IS NULL"
        )
        connection.execute(
            "CREATE TABLE IF NOT EXISTS receipt_imports(id TEXT PRIMARY KEY,user_id INTEGER NOT NULL REFERENCES users(id),provider TEXT NOT NULL,image BLOB NOT NULL,extracted TEXT NOT NULL,created REAL NOT NULL,entry_id TEXT UNIQUE REFERENCES entries(id))"
        )
        closing_columns = {
            row["name"] for row in connection.execute("PRAGMA table_info(closings)")
        }
        if "business_date" not in closing_columns:
            connection.execute("ALTER TABLE closings ADD COLUMN business_date TEXT")
        connection.execute(
            "CREATE UNIQUE INDEX IF NOT EXISTS one_close_per_day ON closings(business_date) WHERE business_date IS NOT NULL"
        )
        # Legacy postings gain local dates without changing their recorded movements.
        for row in connection.execute(
            "SELECT id,created FROM entries WHERE business_date IS NULL"
        ).fetchall():
            connection.execute(
                "UPDATE entries SET business_date=? WHERE id=?",
                (clock.business_day(row["created"]), row["id"]),
            )
        connection.execute(
            "UPDATE entries SET collected_fee=cash_delta+wallet_delta WHERE collected_fee IS NULL AND type IN ('cash_in','cash_out') AND cash_delta+wallet_delta>=0"
        )
        if not connection.execute("SELECT 1 FROM accounts").fetchone():
            connection.executemany(
                "INSERT INTO accounts(name,provider,kind) VALUES(?,?,?)",
                [
                    (n, p, k)
                    for (n, p, k) in [
                        ("KBZPay · Normal", "KBZPay", "Normal"),
                        ("KBZPay · Merchant", "KBZPay", "Merchant"),
                        ("KBZPay · MMQR Red", "KBZPay", "MMQR Business"),
                        ("WavePay · Normal", "WavePay", "Normal"),
                        ("Wave · Channel", "WavePay", "Channel"),
                    ]
                ],
            )
