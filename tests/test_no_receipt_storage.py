"""Extraction/cancellation leaves no persistent receipt or draft records."""

from unittest.mock import patch
from counter import database
from tests.support import LedgerFixture


class NoReceiptStorageTests(LedgerFixture):
    def test_extraction_returns_fields_without_persistent_storage(self):
        before = self.counts()
        with database.connect() as connection:
            entries_before = connection.execute(
                "SELECT count(*) FROM entries"
            ).fetchone()[0]
        fields = dict(
            provider="KBZPay",
            amount=100000,
            customer="Test Customer",
            text="Private OCR text",
        )
        with patch("counter.http.extract_image", return_value=(b"photo bytes", fields)):
            code, result = self.req(
                "receipt/extract", provider="KBZPay", image="fixture"
            )
        self.assertEqual(code, 200)
        self.assertEqual(result["amount"], 100000)
        self.assertNotIn("import_id", result)
        self.assertNotIn("text", result)
        self.assertEqual(self.counts(), before)
        with database.connect() as connection:
            self.assertIsNone(
                connection.execute(
                    "SELECT name FROM sqlite_master WHERE name='receipt_imports'"
                ).fetchone()
            )
            self.assertEqual(
                connection.execute("SELECT count(*) FROM entries").fetchone()[0],
                entries_before,
            )

    def test_legacy_image_storage_is_removed_without_changing_entries(self):
        before = self.counts()
        with database.connect() as connection:
            entries = connection.execute("SELECT * FROM entries ORDER BY id").fetchall()
            connection.execute(
                "CREATE TABLE receipt_imports(id TEXT,image BLOB,extracted TEXT)"
            )
            connection.execute(
                "INSERT INTO receipt_imports VALUES(?,?,?)", ("legacy", b"photo", "{}")
            )
        database.initialize()
        with database.connect() as connection:
            self.assertIsNone(
                connection.execute(
                    "SELECT name FROM sqlite_master WHERE name='receipt_imports'"
                ).fetchone()
            )
            self.assertEqual(
                connection.execute("SELECT * FROM entries ORDER BY id").fetchall(),
                entries,
            )
        self.assertEqual(self.counts(), before)

    def test_obsolete_import_reference_does_not_silently_post(self):
        before = self.counts()
        self.assertEqual(
            self.entry("obsolete", "cash_in", 1000, 1, receipt_import_id="old-id")[0],
            400,
        )
        self.assertEqual(self.counts(), before)
