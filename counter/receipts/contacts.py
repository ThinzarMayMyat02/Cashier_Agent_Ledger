"""Conservative customer/contact pairing shared by verified receipt layouts."""

import re


def customer_from_contact_pair(lines):
    """Read a unique adjacent name/contact pair when OCR cannot read labels."""
    contact_pattern = r"\(?([*•xX]{2,}\d{3,}|(?:09|\+?959)\d{7,10})\)?"
    candidates = []
    for index, line in enumerate(lines):
        match = re.fullmatch(contact_pattern, line.strip())
        if not match or index == 0:
            continue
        name = lines[index - 1].strip()
        # A name must contain letters, with no currency, timestamp, or field label.
        if not re.fullmatch(
            r"[A-Za-z\u1000-\u109f][A-Za-z\u1000-\u109f .’'-]{2,99}", name
        ):
            continue
        if name.lower() in {
            "payment successful",
            "transaction no",
            "transaction time",
            "transfer from",
            "transfer to",
            "customer name",
        }:
            continue
        candidates.append((name, match.group(1)))
    return candidates[0] if len(candidates) == 1 else ("", "")
