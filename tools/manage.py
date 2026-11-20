"""Cloud operator commands. Passwords and financial data never enter Git."""

import argparse
import base64
import getpass
import os
import shutil
import sqlite3
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


def check_ocr():
    from counter.receipts.reader import extract_image, selected_backend

    backend = selected_backend()
    if backend != "tesseract":
        raise ValueError(
            "Set LEDGER_OCR_BACKEND=tesseract to check the cloud OCR backend"
        )
    try:
        from PIL import Image, ImageDraw, ImageFont
        import zxingcpp
    except ImportError as error:
        raise ValueError(
            "Install requirements.txt in the web app's virtualenv"
        ) from error
    image = Image.new("RGB", (700, 140), "white")
    ImageDraw.Draw(image).text(
        (30, 40), "100,000.00 Ks", fill="black", font=ImageFont.load_default(size=40)
    )
    with tempfile.TemporaryDirectory() as directory:
        path = Path(directory) / "check.png"
        image.save(path)
        _, extracted = extract_image(
            base64.b64encode(path.read_bytes()).decode(), "KBZPay"
        )
        from counter.receipts.tesseract_reader import _recognize_words

        executable = os.environ.get("LEDGER_TESSERACT_CMD") or shutil.which("tesseract")
        # Loading Myanmar against a synthetic image checks model compatibility.
        _recognize_words(executable, path, "mya", 7)
    if extracted["amount"] != 100000:
        raise ValueError(
            "Tesseract smoke test did not read 100,000 MMK. Check engine and models."
        )
    from counter.receipts.tesseract_reader import TESSDATA_PATH

    if not (TESSDATA_PATH / "mya.traineddata").is_file():
        raise ValueError("Myanmar OCR model is missing")
    print(
        "OCR ready: Tesseract, English model, Myanmar model, Pillow and QR decoder available."
    )
    print(
        "Synthetic amount read correctly. Verify your actual receipts before customer use."
    )


def init_owner(name):
    from counter import auth, database

    password = getpass.getpass("Owner password (at least 10 characters): ")
    if password != getpass.getpass("Repeat password: "):
        raise ValueError("Passwords do not match")
    database.initialize()
    with database.connect() as connection:
        connection.execute("BEGIN IMMEDIATE")
        token = auth.sign_in(connection, dict(name=name, password=password), setup=True)
        # Setup here creates no browser session or reusable console token.
        connection.execute("DELETE FROM sessions WHERE token=?", (token,))
    print("Owner created. Sign in through your HTTPS website.")


def backup_database(output):
    from counter import database

    source = Path(database.DB).resolve()
    destination = Path(output).resolve()
    if not source.is_file():
        raise ValueError("Database does not exist; check LEDGER_DB")
    if destination.exists():
        raise ValueError("Backup path already exists; choose a new filename")
    destination.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    with sqlite3.connect(source.as_uri() + "?mode=ro", uri=True) as connection:
        with sqlite3.connect(destination) as target:
            connection.backup(target)
    destination.chmod(0o600)
    print("Backup saved. Download it privately and keep it outside the repository.")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("check-ocr")
    owner = commands.add_parser("init-owner")
    owner.add_argument("--name", required=True)
    backup = commands.add_parser("backup")
    backup.add_argument("--output", required=True)
    options = parser.parse_args()
    try:
        if options.command == "check-ocr":
            check_ocr()
        elif options.command == "init-owner":
            init_owner(options.name)
        else:
            backup_database(options.output)
    except (ValueError, OSError, sqlite3.Error) as error:
        parser.exit(1, str(error) + "\n")


if __name__ == "__main__":
    main()
