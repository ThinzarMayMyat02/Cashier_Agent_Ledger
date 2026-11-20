"""Myanmar OCR output remains reviewed input."""

import json
import subprocess
import unittest
from unittest.mock import patch
from counter.receipts.myanmar import read_customer_name


class MyanmarOCRTests(unittest.TestCase):
    def test_name_without_crop_border(self):
        result = subprocess.CompletedProcess(
            [], 0, json.dumps({"text": "ဦးလှမြိုင် |\n", "confidence": 93}).encode(), b""
        )
        with patch("counter.receipts.myanmar.subprocess.run", return_value=result):
            self.assertEqual(read_customer_name("sample.png"), "ဦးလှမြိုင်")

    def test_low_confidence_requires_manual_entry(self):
        result = subprocess.CompletedProcess(
            [], 0, json.dumps({"text": "ဦးလှမြိုင်", "confidence": 20}).encode(), b""
        )
        with patch("counter.receipts.myanmar.subprocess.run", return_value=result):
            self.assertEqual(read_customer_name("sample.png"), "")
