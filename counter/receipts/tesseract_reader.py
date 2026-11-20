"""Portable, local-only Tesseract OCR and QR decoding for Linux/WSGI hosts."""

import csv
import io
import os
import re
import shutil
import subprocess
from pathlib import Path

TESSDATA_PATH = Path(__file__).with_name("tessdata")
MAX_PIXELS = 25_000_000
MAX_DIMENSION = 10_000


def read_image(image_path):
    try:
        from PIL import Image, ImageOps
        import zxingcpp
    except ImportError as error:
        raise ValueError(
            "Linux OCR dependencies are missing. Install requirements.txt."
        ) from error
    executable = os.environ.get("LEDGER_TESSERACT_CMD") or shutil.which("tesseract")
    if not executable:
        raise ValueError(
            "Tesseract is not installed. Ask the owner to run the OCR check."
        )
    try:
        with Image.open(image_path) as source:
            width, height = source.size
            if source.format not in ("PNG", "JPEG") or not (
                0 < width <= MAX_DIMENSION
                and 0 < height <= MAX_DIMENSION
                and width * height <= MAX_PIXELS
            ):
                raise ValueError("Invalid or oversized image")
            source.load()
            normalized = ImageOps.exif_transpose(source).convert("RGB")
    except (OSError, Image.DecompressionBombError) as error:
        raise ValueError(
            "Could not read this image. Try a clearer PNG or JPEG."
        ) from error
    qr_payloads = [
        barcode.text
        for barcode in zxingcpp.read_barcodes(
            normalized, formats=zxingcpp.BarcodeFormat.QRCode
        )
        if barcode.valid
    ]
    normalized.thumbnail((2400, 2400))
    normalized_path = Path(image_path).with_name("normalized.png")
    normalized.save(normalized_path)
    words = _recognize_words(executable, normalized_path, "eng", 11)
    lines = _ordered_lines(words, normalized.width)
    _read_myanmar_customer_name(executable, normalized, words, Path(image_path).parent)
    return {
        "lines": lines,
        "qr": qr_payloads,
        "customer_name": _wave_customer_name(words, normalized.width),
    }


def _recognize_words(executable, image_path, language, page_segmentation):
    command = [
        executable,
        str(Path(image_path).resolve()),
        "stdout",
        "--tessdata-dir",
        str(TESSDATA_PATH),
        "-l",
        language,
        "--oem",
        "1",
        "--psm",
        str(page_segmentation),
        "-c",
        "tessedit_create_tsv=1",
    ]
    try:
        result = subprocess.run(
            command,
            capture_output=True,
            timeout=40,
            check=True,
            env=dict(os.environ, OMP_THREAD_LIMIT="1"),
        )
        rows = csv.DictReader(
            io.StringIO(result.stdout.decode("utf-8")), delimiter="\t"
        )
        required_columns = {
            "level",
            "text",
            "left",
            "top",
            "width",
            "height",
            "conf",
            "page_num",
            "block_num",
            "par_num",
            "line_num",
        }
        if not required_columns.issubset(rows.fieldnames or []):
            raise ValueError("Invalid Tesseract TSV output")
        return [
            dict(
                text=row["text"].strip(),
                left=int(row["left"]),
                top=int(row["top"]),
                width=int(row["width"]),
                height=int(row["height"]),
                confidence=float(row["conf"]),
                line=(
                    row["page_num"],
                    row["block_num"],
                    row["par_num"],
                    row["line_num"],
                ),
            )
            for row in rows
            if row.get("level") == "5" and row.get("text", "").strip()
        ]
    except (subprocess.SubprocessError, OSError, ValueError, KeyError) as error:
        raise ValueError(
            "Could not read this receipt. Check Tesseract/models or use manual entry."
        ) from error


def _ordered_lines(words, image_width):
    grouped = {}
    for word in words:
        grouped.setdefault(word["line"], []).append(word)
    fragments = []
    for line_words in grouped.values():
        line_words.sort(key=lambda word: word["left"])
        fragment = []
        for word in line_words:
            if (
                fragment
                and word["left"] - (fragment[-1]["left"] + fragment[-1]["width"])
                > image_width * 0.06
            ):
                fragments.append(fragment)
                fragment = []
            fragment.append(word)
        if fragment:
            fragments.append(fragment)
    # Vision and this backend both expose text fragments in visual reading order.
    fragments.sort(
        key=lambda fragment: (
            round(min(word["top"] + word["height"] / 2 for word in fragment) / 15),
            fragment[0]["left"],
        )
    )
    return [" ".join(word["text"] for word in fragment) for fragment in fragments]


def _read_myanmar_customer_name(executable, image, words, directory):
    """Crop only the customer-name value; do not OCR arbitrary personal fields."""
    for index, word in enumerate(words):
        if word["text"].lower() != "customer":
            continue
        following = [
            candidate
            for candidate in words[index + 1 : index + 4]
            if candidate["line"] == word["line"]
        ]
        if not any(
            candidate["text"].lower().strip(":.") == "name" for candidate in following
        ):
            continue
        # Myanmar glyphs are taller than the English label. Leave enough vertical
        # whitespace for Tesseract's line segmentation rather than clipping marks.
        top = max(0, int(word["top"] - word["height"] * 2.5))
        bottom = min(image.height, word["top"] + word["height"] * 4)
        crop = image.crop(
            (int(image.width * 0.55), top, int(image.width * 0.96), bottom)
        )
        crop_path = directory / "customer-name.png"
        crop = crop.resize((crop.width * 3, crop.height * 3))
        crop.save(crop_path)
        try:
            recognized = _recognize_words(executable, crop_path, "mya", 7)
        except ValueError:
            return
        name = " ".join(item["text"] for item in recognized).strip(" |")
        confidence = (
            sum(item["confidence"] for item in recognized) / len(recognized)
            if recognized
            else 0
        )
        if (
            confidence >= 60
            and re.search(r"[\u1000-\u109f]", name)
            and len(name) <= 100
        ):
            (directory / "customer-name.txt").write_text(name, encoding="utf-8")
        break


def _wave_customer_name(words, image_width):
    """Read a confident Normal Wave name even when its masked phone is unreadable."""
    text = " ".join(word["text"] for word in words)
    if not re.search(r"\b(?:Send|Receive) Money\b", text, re.I):
        return ""
    identifiers = [word for word in words if re.fullmatch(r"\d{10}", word["text"])]
    if len(identifiers) != 1:
        return ""
    identifier_top = identifiers[0]["top"]
    grouped = {}
    for word in words:
        if (
            word["left"] >= image_width * 0.35
            and 0 < identifier_top - word["top"] < image_width * 0.35
        ):
            grouped.setdefault(word["line"], []).append(word)
    candidates = []
    for line_words in grouped.values():
        line_words.sort(key=lambda word: word["left"])
        name = " ".join(word["text"] for word in line_words)
        if (
            len(line_words) >= 2
            and all(word["confidence"] >= 75 for word in line_words)
            and re.fullmatch(r"[A-Za-z][A-Za-z .’'-]{2,99}", name)
            and name.lower() not in ("send money", "receive money")
        ):
            candidates.append(name)
    return candidates[0] if len(candidates) == 1 else ""
