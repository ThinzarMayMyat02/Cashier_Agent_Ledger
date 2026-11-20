"""Local receipt extraction with selectable macOS Vision or portable Tesseract."""

import base64
import hashlib
import json
import os
import subprocess
import sys
import tempfile
import threading
from pathlib import Path
from .parser import parse_receipt
from .myanmar import read_customer_name

_compile_lock = threading.Lock()
_read_slots = threading.BoundedSemaphore(2)
MAX_IMAGE_BYTES = 5 * 1024 * 1024


def selected_backend():
    backend = os.environ.get("LEDGER_OCR_BACKEND", "auto").lower()
    if backend == "auto":
        return "vision" if sys.platform == "darwin" else "tesseract"
    if backend not in ("vision", "tesseract"):
        raise ValueError("Select auto, vision or tesseract as the OCR backend")
    return backend


def extract_image(encoded, provider):
    if provider not in ("KBZPay", "WavePay"):
        raise ValueError("Select KBZPay or WavePay")
    image = _decode_upload(encoded)
    backend = selected_backend()
    if not _read_slots.acquire(blocking=False):
        raise ValueError("Receipt reader is busy. Try again shortly.")
    try:
        with tempfile.TemporaryDirectory(prefix="counter-receipt-") as directory:
            image_path = Path(directory) / "receipt"
            image_path.write_bytes(image)
            if backend == "vision":
                result = _read_with_vision(image_path)
            else:
                from .tesseract_reader import read_image

                result = read_image(image_path)
            parsed = parse_receipt(result, provider)
            parsed["ocr_backend"] = backend
            name_path = Path(directory) / "customer-name.txt"
            crop_path = Path(directory) / "customer-name.png"
            name = name_path.read_text(encoding="utf-8") if name_path.is_file() else ""
            if (
                not name
                and not parsed.get("customer")
                and backend == "vision"
                and crop_path.is_file()
            ):
                name = read_customer_name(crop_path)
            name_engine = "myanmar"
            if not name and not parsed.get("customer") and result.get("customer_name"):
                name = result["customer_name"]
                name_engine = "tesseract"
            if name:
                parsed["customer"] = name
                parsed["customer_ocr"] = name_engine
                parsed["warnings"] = [
                    message
                    for message in parsed["warnings"]
                    if message
                    != "Customer name could not be read. Enter it manually if available."
                ]
        return image, parsed
    finally:
        _read_slots.release()


def _decode_upload(encoded):
    try:
        image = base64.b64decode(encoded, validate=True)
    except (ValueError, TypeError) as error:
        raise ValueError("Invalid image") from error
    if (
        not image
        or len(image) > MAX_IMAGE_BYTES
        or not (
            image.startswith(b"\x89PNG\r\n\x1a\n") or image.startswith(b"\xff\xd8\xff")
        )
    ):
        raise ValueError("Choose a PNG or JPEG image up to 5 MB")
    return image


def _read_with_vision(image_path):
    if sys.platform != "darwin":
        raise ValueError(
            "Vision OCR requires macOS. Select the tesseract backend on Linux."
        )
    source = Path(__file__).with_name("receipt_reader.swift")
    digest = hashlib.sha256(source.read_bytes()).hexdigest()[:16]
    executable = Path(tempfile.gettempdir()) / ("counter-receipt-" + digest)
    with _compile_lock:
        if not executable.exists():
            try:
                subprocess.run(
                    ["/usr/bin/swiftc", str(source), "-o", str(executable)],
                    capture_output=True,
                    timeout=120,
                    check=True,
                )
            except (subprocess.SubprocessError, OSError) as error:
                raise ValueError(
                    "Receipt reader could not start. Try manual entry."
                ) from error
    try:
        result = subprocess.run(
            [str(executable), str(image_path)],
            capture_output=True,
            timeout=45,
            check=True,
        )
        return json.loads(result.stdout)
    except (subprocess.SubprocessError, ValueError, OSError) as error:
        raise ValueError(
            "Could not read this image. Try a clearer PNG or JPEG."
        ) from error
