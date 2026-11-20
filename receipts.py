"""Compatibility imports. Receipt implementation lives in counter.receipts."""

from counter.receipts.parser import parse_receipt
from counter.receipts.reader import extract_image

__all__ = ["parse_receipt", "extract_image"]
