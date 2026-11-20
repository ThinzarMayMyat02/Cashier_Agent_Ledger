"""Map unverified OCR and QR data into an editable transaction fields."""

import base64
import json
import re
from .contacts import customer_from_contact_pair
from .wavepay import wavepay_fields


def parse_receipt(result, provider):
    lines = result.get("lines", [])
    text = "\n".join(lines)
    transaction_id = ""
    qr_id = ""
    warnings = [
        "Check every field against the receipt. This import does not verify payment."
    ]
    for payload in result.get("qr", []):
        if provider != "KBZPay" or not payload.startswith("KPRSC."):
            continue
        try:
            part = payload.split(".")[1]
            info = json.loads(base64.urlsafe_b64decode(part + "=" * (-len(part) % 4)))
            candidate = info.get("tid", "")
            if isinstance(candidate, str) and re.fullmatch(
                "[A-Za-z0-9-]{6,80}", candidate
            ):
                qr_id = candidate
        except (ValueError, IndexError, TypeError):
            continue
    for i, line in enumerate(lines):
        if re.search(
            "(transaction\\s*(?:no\\.?|id|number)|reference\\s*(?:no\\.?|id)|လုပ်ငန်းစဉ်အမှတ်)",
            line,
            re.I,
        ):
            rest = re.sub(
                "^.*?(?:transaction\\s*(?:number|no\\.?|id)|reference\\s*(?:no\\.?|id)|လုပ်ငန်းစဉ်အမှတ်)\\s*[:#-]?\\s*",
                "",
                line,
                flags=re.I,
            )
            candidates = [rest] + lines[i + 1 : i + 2]
            for candidate in candidates:
                if re.fullmatch("[A-Za-z0-9-]{6,80}", candidate.strip()):
                    transaction_id = candidate.strip()
                    break
            if transaction_id:
                break
    if qr_id:
        if transaction_id and transaction_id != qr_id:
            warnings.append("QR and printed transaction IDs differ. Check carefully.")
        transaction_id = qr_id
    amounts = []
    for line in lines:
        match = re.search(
            "[-−]?\\s*(\\d[\\d,]*(?:\\.\\d{2})?)\\s*(?:\\(?Ks\\)?|MMK|ကျပ်)", line, re.I
        )
        if match:
            value = match.group(1).replace(",", "")
            (whole, _, fraction) = value.partition(".")
            if fraction and fraction != "00":
                warnings.append(
                    "Receipt has fractional kyat. Enter the correct whole MMK amount."
                )
                continue
            number = int(whole)
            if 0 < number <= 100000000000:
                amounts.append(number)
    unique = set(amounts)
    amount = next(iter(unique)) if len(unique) == 1 else None
    if amount is None:
        warnings.append("Amount is missing or ambiguous. Enter it manually.")
    timestamp = re.search(
        "\\b\\d{1,2}[/.-]\\d{1,2}[/.-]\\d{4}[T\\s-]+\\d{1,2}:\\d{2}(?::\\d{2})?", text
    )
    if not transaction_id:
        warnings.append(
            "Transaction ID could not be read. Enter it manually if available."
        )
    details = receipt_details(lines)
    if provider == "KBZPay":
        if not transaction_id:
            identifiers = {
                line.strip() for line in lines if re.fullmatch(r"\d{20}", line.strip())
            }
            if len(identifiers) == 1:
                transaction_id = identifiers.pop()
                warnings = [
                    message
                    for message in warnings
                    if message
                    != "Transaction ID could not be read. Enter it manually if available."
                ]
        if not details["customer"]:
            customer, contact = customer_from_contact_pair(lines)
            if customer:
                details["customer"] = customer
                if re.search(r"[*•xX]", contact):
                    details["masked_phone"] = contact
                else:
                    details["phone"] = contact
    if details["total_amount"] is not None:
        amount = details["total_amount"]
        warnings = [
            w
            for w in warnings
            if w != "Amount is missing or ambiguous. Enter it manually."
        ]
    receipt_time = timestamp.group(0) if timestamp else ""
    if provider == "WavePay":
        wave = wavepay_fields(lines)
        if wave:
            details.update(
                {
                    key: value
                    for key, value in wave.items()
                    if key not in ("provider_transaction_id", "receipt_time")
                }
            )
            transaction_id = wave["provider_transaction_id"] or transaction_id
            receipt_time = wave["receipt_time"] or receipt_time
            amount = (
                wave["total_amount"] if wave["total_amount"] is not None else amount
            )
            if wave.get("receipt_format") == "wave_channel":
                amount = wave["receipt_principal"]
            if transaction_id:
                warnings = [
                    message
                    for message in warnings
                    if message
                    != "Transaction ID could not be read. Enter it manually if available."
                ]
            if amount is not None:
                warnings = [
                    message
                    for message in warnings
                    if message != "Amount is missing or ambiguous. Enter it manually."
                ]

    if not details["customer"]:
        warnings.append(
            "Customer name could not be read. Enter it manually if available."
        )
    if not receipt_time:
        date = label_value(lines, r"transaction\s*time")
        if re.fullmatch(r"\d{8}", date):
            from datetime import datetime

            try:
                receipt_time = datetime.strptime(date, "%Y%m%d").strftime("%d/%m/%Y")
            except ValueError:
                pass
    return dict(
        **details,
        provider=provider,
        provider_transaction_id=transaction_id,
        amount=amount,
        receipt_time=receipt_time,
        warnings=warnings,
        text=text[:12000],
        qr_id_detected=bool(qr_id),
    )


def label_value(lines, label):
    """Read an OCR label's inline value or the next non-label line."""
    for index, line in enumerate(lines):
        match = re.match(r"^\s*(?:" + label + r")\s*[:.]?\s*(.*)$", line, re.I)
        if match:
            if match.group(1).strip():
                return match.group(1).strip()
            if index + 1 < len(lines):
                candidate = lines[index + 1].strip()
                return "" if candidate.endswith(":") else candidate
    return ""


def currency_value(text):
    match = re.search(
        r"[+−-]?\s*(\d[\d,]*)(?:\.(\d{2}))?\s*(?:\(?Ks\)?|MMK|ကျပ်)", text, re.I
    )
    if not match or (match.group(2) and match.group(2) != "00"):
        return None
    value = int(match.group(1).replace(",", ""))
    return value if 0 < value <= 100000000000 else None


def receipt_details(lines):
    total = currency_value(label_value(lines, r"total\s*(?:amount|amt)"))
    principal = currency_value(label_value(lines, r"amount"))
    provider_fee = currency_value(label_value(lines, r"fees?"))
    if total is None:
        amounts = {currency_value(line) for line in lines}
        amounts.discard(None)
        if len(amounts) == 1:
            total = amounts.pop()
    signed = []
    for line in lines:
        match = re.search(
            r"([+−-])\s*\d[\d,]*(?:\.\d{2})?\s*(?:\(?Ks\)?|MMK)", line, re.I
        )
        if match:
            signed.append("cash_out" if match.group(1) == "+" else "cash_in")
    direction = signed[0] if signed and len(set(signed)) == 1 else ""
    customer = label_value(lines, r"transfer\s*(?:from|to)|customer\s*name")
    phone_match = re.search(r"\(?([*•xX]{2,}\d{3,}|(?:\+?959|09)\d{5,})\)?", customer)
    masked_phone = phone_match.group(1) if phone_match else ""
    if phone_match:
        customer = customer[: phone_match.start()].strip()
    # Masked phone details often occupy the following OCR line.
    if not masked_phone:
        for i, line in enumerate(lines):
            if customer and line.strip() == customer and i + 1 < len(lines):
                match = re.fullmatch(r"\(?([*•xX]{2,}\d{3,})\)?", lines[i + 1].strip())
                if match:
                    masked_phone = match.group(1)
    full_phone = (
        masked_phone
        if masked_phone
        and "*" not in masked_phone
        and "•" not in masked_phone
        and "x" not in masked_phone.lower()
        else ""
    )
    return dict(
        total_amount=total,
        receipt_principal=principal,
        provider_fee=provider_fee,
        transaction_type=direction,
        customer=customer,
        phone=full_phone,
        masked_phone=masked_phone if not full_phone else "",
    )
