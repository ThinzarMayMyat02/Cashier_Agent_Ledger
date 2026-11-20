"""Local Myanmar recognition for customer-name regions omitted by Apple Vision."""

import json
import re
import shutil
import subprocess
from pathlib import Path


def read_customer_name(image_path):
    executable = shutil.which("node")
    if not executable:
        for candidate in ("/opt/homebrew/bin/node", "/usr/local/bin/node"):
            if Path(candidate).is_file():
                executable = candidate
                break
    root = Path(__file__).resolve().parents[2]
    script = root / "tools/ocr/read-name.cjs"
    model = Path(__file__).with_name("tessdata") / "mya.traineddata"
    if not executable or not script.is_file() or not model.is_file():
        return ""
    try:
        process = subprocess.run(
            [executable, str(script), str(image_path)],
            capture_output=True,
            timeout=45,
            check=True,
        )
        result = json.loads(process.stdout)
    except (subprocess.SubprocessError, OSError, ValueError):
        return ""
    name = " ".join(result["text"].split()).strip(" |")
    if result.get("confidence", 0) < 60:
        return ""
    if not re.search(r"[\u1000-\u109f]", name) or len(name) > 100:
        return ""
    return name
