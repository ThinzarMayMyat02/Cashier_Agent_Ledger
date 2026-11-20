"""Whole-kyat input validation, fee policy and posting amounts."""

from __future__ import annotations
from dataclasses import dataclass


def whole_amount(value, minimum=0, maximum=100000000000):
    if type(value) == int:
        result = value
    elif isinstance(value, str) and value.isascii() and value.isdigit():
        result = int(value)
    else:
        raise ValueError("Enter a whole MMK amount")
    if not minimum <= result <= maximum:
        raise ValueError("Amount out of range")
    return result


def calculate_fee(entry_type, amount):
    """Return the suggestion. The confirmed collected fee is recorded separately."""
    if entry_type == "cash_in":
        return (amount + 99999) // 100000 * 100
    if entry_type != "cash_out":
        raise ValueError("Invalid fee type")
    if amount <= 10000:
        return 100
    if amount <= 50000:
        return 300
    if amount < 2000000:
        return max(1, amount // 100000) * 500
    return (amount + 125) // 250


@dataclass(frozen=True)
class PostingAmounts:
    """Validated monetary effects and the fee audit fields for one posting."""

    suggested_fee: int
    collected_fee: int
    fee_mode: str | None
    override_reason: str
    cash_delta: int
    wallet_delta: int


def prepare_posting_amounts(data, entry_type, amount, account_id):
    """Validate fees and selected-wallet movements before database writes."""
    suggested = (
        calculate_fee(entry_type, amount)
        if entry_type in ["cash_in", "cash_out"]
        else 0
    )
    collected_fee = 0
    fee_mode = None
    override_reason = ""
    if entry_type in ["cash_in", "cash_out"]:
        fee_mode = data.get("fee_mode", "deduct")
        if fee_mode not in ["deduct", "separate"]:
            raise ValueError("Invalid fee collection mode")
        if "fee" in data:
            collected_fee = whole_amount(data["fee"], 0, amount)
        elif "cash_amount" in data:
            actual = whole_amount(data["cash_amount"])
            collected_fee = (
                actual - amount if entry_type == "cash_in" else amount - actual
            )
            if not 0 <= collected_fee <= amount:
                raise ValueError("Cash movement does not match a valid collected fee")
        else:
            collected_fee = suggested
        if not 0 <= collected_fee <= amount or (
            entry_type == "cash_out"
            and fee_mode == "deduct"
            and (collected_fee >= amount)
        ):
            raise ValueError("Fee must leave a positive payout")
        override_reason = str(data.get("override_reason", "")).strip()
        expected_cash = (
            amount + collected_fee
            if entry_type == "cash_in"
            else amount - collected_fee if fee_mode == "deduct" else amount
        )
        if "cash_amount" in data and whole_amount(data["cash_amount"]) != expected_cash:
            raise ValueError("Cash amount and fee disagree; refresh and confirm")
        if (
            entry_type == "cash_out"
            and fee_mode == "separate"
            and (whole_amount(data.get("fee_cash_received", -1)) != collected_fee)
        ):
            raise ValueError("Confirm the separately collected cash fee")
        cash = (
            amount + collected_fee
            if entry_type == "cash_in"
            else collected_fee - amount
        )
        wallet = -amount if entry_type == "cash_in" else amount
    else:
        sign = 1 if entry_type == "funds_in" else -1
        cash = sign * amount if not account_id else 0
        wallet = sign * amount if account_id else 0
        if not str(data.get("note", "")).strip():
            raise ValueError("Add an expense category or reason")
    return PostingAmounts(
        suggested, collected_fee, fee_mode, override_reason, cash, wallet
    )
