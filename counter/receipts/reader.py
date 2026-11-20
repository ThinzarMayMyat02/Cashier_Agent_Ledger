"""Local receipt extraction. A decoded QR is unverified input, never payment proof."""

import base64
import hashlib
import json
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


def extract_image(encoded, provider):
    if provider not in ("KBZPay", "WavePay"):
        raise ValueError("Select KBZPay or WavePay")
    try:
        image = base64.b64decode(encoded, validate=True)
    except (ValueError, TypeError):
        raise ValueError("Invalid image")
    if not image or len(image) > MAX_IMAGE_BYTES:
        raise ValueError("Choose a PNG or JPEG image up to 5 MB")
    if not (
        image.startswith(b"\x89PNG\r\n\x1a\n") or image.startswith(b"\xff\xd8\xff")
    ):
        raise ValueError("Choose a PNG or JPEG image up to 5 MB")
    if sys.platform != "darwin":
        raise ValueError("Local receipt reading currently requires a Mac server")
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
            except (subprocess.SubprocessError, OSError):
                raise ValueError("Receipt reader could not start. Try manual entry.")
    if not _read_slots.acquire(blocking=False):
        raise ValueError("Receipt reader is busy. Try again shortly.")
    try:
        with tempfile.TemporaryDirectory(prefix="counter-receipt-") as directory:
            path = Path(directory) / "receipt"
            path.write_bytes(image)
            try:
                process = subprocess.run(
                    [str(executable), str(path)],
                    capture_output=True,
                    timeout=45,
                    check=True,
                )
                result = json.loads(process.stdout)
            except (subprocess.SubprocessError, ValueError, OSError):
                raise ValueError(
                    "Could not read this image. Try a clearer PNG or JPEG."
                )
            parsed = parse_receipt(result, provider)
            customer_crop = Path(directory) / "customer-name.png"
            if not parsed.get("customer") and customer_crop.is_file():
                name = read_customer_name(customer_crop)
                if name:
                    parsed["customer"] = name
                    parsed["warnings"] = [
                        message
                        for message in parsed["warnings"]
                        if message
                        != "Customer name could not be read. Enter it manually if available."
                    ]
                    parsed["customer_ocr"] = "myanmar"
        return image, parsed
    finally:
        _read_slots.release()
