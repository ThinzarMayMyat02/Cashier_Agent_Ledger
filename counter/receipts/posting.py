"""Receipt-only posting validation, participating in the caller's transaction."""

import re
from dataclasses import dataclass
from ..fees import whole_amount

WAVE_CHANNEL_FORMAT = "wave_channel"


@dataclass(frozen=True)
class ProviderAdjustments:
    """Wallet income/expense independent of the collected customer fee."""

    commission: int
    fee: int

    @property
    def wallet_delta(self):
        return self.commission - self.fee


def validate_receipt_review(data, account, entry_type):
    """Validate operator-reviewed metadata. OCR is assistance, never payment proof."""
    if data.get("receipt_import_id"):
        raise ValueError("This import form is outdated. Import the receipt again.")
    receipt = data.get("receipt")
    if receipt is None:
        return {}
    if not isinstance(receipt, dict):
        raise ValueError("Invalid receipt information")
    if (
        entry_type not in ("cash_in", "cash_out")
        or not account
        or receipt.get("provider") not in ("KBZPay", "WavePay")
        or account["provider"].lower() != receipt["provider"].lower()
    ):
        raise ValueError("Select a wallet matching the receipt provider")
    if data.get("receipt_confirmed") is not True:
        raise ValueError("Review the receipt and confirm all details first")
    receipt_format = receipt.get("receipt_format")
    if receipt_format not in (None, "wave_channel"):
        raise ValueError("Invalid receipt format")
    if receipt_format == WAVE_CHANNEL_FORMAT and (
        receipt["provider"] != "WavePay" or account["kind"].lower() != "channel"
    ):
        raise ValueError("Select a WavePay Channel wallet for this receipt")
    return receipt


def validate_provider_adjustments(data, extracted, entry_type, amount):
    """Allow reviewed Channel adjustments without changing cash or shop fees."""
    adjustments = ProviderAdjustments(
        commission=whole_amount(data.get("provider_commission", 0), 0, amount),
        fee=whole_amount(data.get("provider_fee", 0), 0, amount),
    )
    is_channel = extracted.get("receipt_format") == WAVE_CHANNEL_FORMAT
    if is_channel and not all(
        key in data for key in ("provider_commission", "provider_fee")
    ):
        raise ValueError("Review the provider commission and fee before confirming")
    if (adjustments.commission or adjustments.fee) and not is_channel:
        raise ValueError("Provider adjustments require a Wave Channel receipt")
    if is_channel:
        principal_delta = -amount if entry_type == "cash_in" else amount
        wallet_delta = principal_delta + adjustments.wallet_delta
        if (entry_type == "cash_in" and wallet_delta >= 0) or (
            entry_type == "cash_out" and wallet_delta <= 0
        ):
            raise ValueError("Provider adjustments must leave a valid wallet movement")
    return adjustments


def validate_masked_phone(extracted):
    """Accept only a valid masked contact; never infer hidden digits."""
    contact = extracted.get("masked_phone", "")
    if isinstance(contact, str) and re.fullmatch(r"[*•xX]{2,}\d{3,}", contact):
        return contact
    return None
