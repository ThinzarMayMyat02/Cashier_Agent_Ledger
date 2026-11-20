"""Dispatch verified WavePay Normal and Channel layouts from local OCR lines."""

import re
from datetime import datetime
from .contacts import customer_from_contact_pair
from .wave_channel import (
    TRANSACTION_NUMBER_PATTERN,
    is_channel_layout,
    parse_channel_receipt,
)

CURRENCY_ROW_PATTERN = r"\s*([+−-]?)\s*(\d[\d,]*)\.(\d{2})\s*(?:Ks|MMK)\s*"
TIMESTAMP_PATTERN = r"(\d{1,2}\s+[A-Za-z]{3}\s+\d{4})[ \t]*[•·.+]?[ \t]*(?:\n[^\d\n]*?){0,3}\s*(\d{1,2}:\d{2}\s*[AP]M)"


def wavepay_fields(lines):
    is_channel_cash_in = any(re.search(r"\bcash\s*in\b", line, re.I) for line in lines)
    is_send = is_channel_cash_in or any(
        re.search(r"\bsend\s+money\b", line, re.I) for line in lines
    )
    is_receive = any(re.search(r"\breceive\s+money\b", line, re.I) for line in lines)
    if is_send == is_receive:
        return None

    text = "\n".join(lines)
    timestamp = re.search(TIMESTAMP_PATTERN, text, re.I)
    receipt_time = _read_receipt_time(timestamp)
    amounts = _read_currency_amounts(lines)
    contact_fields = _read_customer_contact(lines)
    transaction_id = _unique_transaction_id(text)
    if amounts is None:
        return dict(
            **contact_fields,
            provider_transaction_id=transaction_id,
            receipt_time=receipt_time,
            transaction_type="",
            total_amount=None,
        )

    header_text = text[: timestamp.start()] if timestamp else ""
    header_amount_count = sum(
        re.fullmatch(CURRENCY_ROW_PATTERN, line, re.I) is not None
        for line in header_text.splitlines()
    )
    if is_channel_layout(is_channel_cash_in, is_receive, header_amount_count):
        return parse_channel_receipt(
            amounts, header_text, receipt_time, is_channel_cash_in
        )

    return dict(
        **contact_fields,
        provider_transaction_id=transaction_id,
        receipt_time=receipt_time,
        transaction_type=_suggest_transaction_type(amounts, is_send),
        total_amount=amounts[-1][0] if amounts and amounts[-1][0] > 0 else None,
        provider_fee=amounts[-2][0] if len(amounts) >= 3 else None,
    )


def _read_receipt_time(timestamp):
    if not timestamp:
        return ""
    try:
        return datetime.strptime(
            timestamp.group(1) + " " + timestamp.group(2).upper(),
            "%d %b %Y %I:%M %p",
        ).strftime("%d/%m/%Y %H:%M:%S")
    except ValueError:
        return ""


def _read_currency_amounts(lines):
    """Keep printed sign with each whole-MMK value; reject fractional kyat."""
    amounts = []
    for line in lines:
        match = re.fullmatch(CURRENCY_ROW_PATTERN, line, re.I)
        if not match:
            continue
        if match.group(3) != "00":
            return None
        amounts.append((int(match.group(2).replace(",", "")), match.group(1)))
    return amounts


def _read_customer_contact(lines):
    customer, contact = customer_from_contact_pair(lines)
    is_masked = bool(re.search(r"[*•xX]", contact))
    return dict(
        customer=customer,
        phone="" if is_masked else contact,
        masked_phone=contact if is_masked else "",
    )


def _unique_transaction_id(text):
    identifiers = set(re.findall(TRANSACTION_NUMBER_PATTERN, text))
    return next(iter(identifiers)) if len(identifiers) == 1 else ""


def _suggest_transaction_type(amounts, is_send):
    for _, sign in amounts:
        if (sign in ("-", "−") and not is_send) or (sign == "+" and is_send):
            return ""
    return "cash_in" if is_send else "cash_out"
