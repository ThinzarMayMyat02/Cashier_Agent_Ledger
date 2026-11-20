"""Portable OCR is local, bounded and never substitutes guessed financial digits."""

import base64
import importlib.util
import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from counter.receipts.reader import extract_image, selected_backend
from counter.receipts.parser import parse_receipt
from counter.receipts.tesseract_reader import (
    _ordered_lines,
    _recognize_words,
)

CLOUD_DEPENDENCIES = bool(
    importlib.util.find_spec("PIL") and importlib.util.find_spec("zxingcpp")
)


class PortableOCRTests(unittest.TestCase):
    def test_linux_selects_tesseract_and_releases_slot_after_failure(self):
        encoded = base64.b64encode(b"\x89PNG\r\n\x1a\nfixture").decode()
        with patch.dict(os.environ, {"LEDGER_OCR_BACKEND": "auto"}), patch(
            "counter.receipts.reader.sys.platform", "linux"
        ):
            self.assertEqual(selected_backend(), "tesseract")
            with patch(
                "counter.receipts.tesseract_reader.read_image",
                side_effect=ValueError("Fixture error"),
            ):
                with self.assertRaises(ValueError):
                    extract_image(encoded, "KBZPay")
            with patch(
                "counter.receipts.tesseract_reader.read_image",
                return_value={"lines": ["100,000.00 Ks"], "qr": []},
            ):
                image, result = extract_image(encoded, "KBZPay")
            self.assertEqual(result["amount"], 100000)
            self.assertEqual(result["ocr_backend"], "tesseract")
            self.assertTrue(image.startswith(b"\x89PNG"))

    def test_invalid_backend_or_image_is_rejected(self):
        with patch.dict(os.environ, {"LEDGER_OCR_BACKEND": "unknown"}):
            with self.assertRaises(ValueError):
                selected_backend()
        for image in ("not base64", base64.b64encode(b"not an image").decode()):
            with self.assertRaises(ValueError):
                extract_image(image, "WavePay")

    def test_tesseract_timeout_and_bad_output_are_errors(self):
        for result in (
            subprocess.TimeoutExpired("tesseract", 40),
            subprocess.CompletedProcess([], 0, b"not TSV", b""),
        ):
            options = (
                {"side_effect": result}
                if isinstance(result, Exception)
                else {"return_value": result}
            )
            with patch("counter.receipts.tesseract_reader.subprocess.run", **options):
                with self.assertRaises(ValueError):
                    _recognize_words("tesseract", Path("fixture.png"), "eng", 11)

    def test_two_columns_are_separate_fragments(self):
        words = [
            dict(
                text="Amount", left=10, top=20, width=90, height=20, line=(1, 1, 1, 1)
            ),
            dict(
                text="100000.00",
                left=500,
                top=20,
                width=120,
                height=20,
                line=(1, 1, 1, 1),
            ),
            dict(text="Ks", left=630, top=20, width=30, height=20, line=(1, 1, 1, 1)),
        ]
        self.assertEqual(_ordered_lines(words, 700), ["Amount", "100000.00 Ks"])

    def test_tesseract_wave_copy_icon_and_split_timestamp(self):
        result = parse_receipt(
            {
                "lines": [
                    "a? Send Money",
                    "1234567890 8",
                    "20 Nov 2026 +",
                    "noise",
                    "06:12 PM",
                    "-300000.00 Ks",
                    "0.00 Ks",
                    "-300000.00 Ks",
                ]
            },
            "WavePay",
        )
        self.assertEqual(result["provider_transaction_id"], "1234567890")
        self.assertEqual(result["receipt_time"], "20/11/2026 18:12:00")
        self.assertEqual(result["amount"], 300000)
        self.assertEqual(result["transaction_type"], "cash_in")
        self.assertEqual(result["phone"], "")

    def test_channel_icon_does_not_hide_commission(self):
        result = parse_receipt(
            {
                "lines": [
                    "C? CashIn",
                    "-30,000.00 Ks",
                    "9.00 Ks",
                    "9770000000",
                    "1234567890 §&",
                    "18 Nov 2026 + 05:50 PM",
                    "-30000.00 Ks",
                    "0.00 Ks",
                    "9.00 Ks",
                    "-29991.00 Ks",
                ]
            },
            "WavePay",
        )
        self.assertEqual(result["receipt_format"], "wave_channel")
        self.assertEqual(result["provider_commission"], 9)
        self.assertEqual(result["amount"], 30000)
        self.assertEqual(result["receipt_wallet_delta"], -29991)

    @unittest.skipUnless(
        CLOUD_DEPENDENCIES, "Install cloud requirements for image validation"
    )
    def test_corrupt_and_oversized_images_are_rejected(self):
        from PIL import Image
        from counter.receipts.tesseract_reader import read_image

        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "receipt.png"
            path.write_bytes(b"\x89PNG\r\n\x1a\ntruncated")
            with patch.dict(os.environ, {"LEDGER_TESSERACT_CMD": "fixture"}):
                with self.assertRaises(ValueError):
                    read_image(path)
                Image.new("RGB", (20, 20), "white").save(path)
                with patch("counter.receipts.tesseract_reader.MAX_PIXELS", 100):
                    with self.assertRaises(ValueError):
                        read_image(path)

    @unittest.skipUnless(
        CLOUD_DEPENDENCIES, "Install cloud requirements for OCR smoke test"
    )
    def test_real_tesseract_synthetic_receipt(self):
        executable = os.environ.get("LEDGER_TESSERACT_CMD") or shutil.which("tesseract")
        if not executable:
            self.skipTest("Install Tesseract for the native OCR smoke test")
        from PIL import Image, ImageDraw, ImageFont

        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "receipt.png"
            image = Image.new("RGB", (700, 140), "white")
            ImageDraw.Draw(image).text(
                (30, 40),
                "100,000.00 Ks",
                fill="black",
                font=ImageFont.load_default(size=40),
            )
            image.save(path)
            with patch.dict(
                os.environ,
                {"LEDGER_OCR_BACKEND": "tesseract", "LEDGER_TESSERACT_CMD": executable},
            ):
                _, extracted = extract_image(
                    base64.b64encode(path.read_bytes()).decode(), "KBZPay"
                )
            self.assertEqual(extracted["amount"], 100000)
            self.assertEqual(extracted["ocr_backend"], "tesseract")
