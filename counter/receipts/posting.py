"""Receipt-only posting validation, participating in the caller's transaction."""

import json
import re
import time
from dataclasses import dataclass
from ..fees import whole_amount
from .drafts import DRAFT_LIFETIME_SECONDS

WAVE_CHANNEL_FORMAT = "wave_channel"


@dataclass(frozen=True)
class ProviderAdjustments:
    """Wallet income/expense independent of the collected customer fee."""

    commission: int
    fee: int

    @property
    def wallet_delta(self):
        return self.commission - self.fee


def load_reviewed_draft(connection, user, data, account, entry_type):
    """Return stored extraction only after ownership, expiry and review checks."""
    import_id = data.get("receipt_import_id")
    if not import_id:
        return {}
    draft = connection.execute(
        "SELECT * FROM receipt_imports WHERE id=? AND user_id=? AND entry_id IS NULL AND created>?",
        (import_id, user["id"], time.time() - DRAFT_LIFETIME_SECONDS),
    ).fetchone()
    if not draft:
        raise ValueError("Receipt draft expired or already used. Import again.")
    if (
        entry_type not in ("cash_in", "cash_out")
        or not account
        or account["provider"].lower() != draft["provider"].lower()
    ):
        raise ValueError("Select a wallet matching the receipt provider")
    if data.get("receipt_confirmed") is not True:
        raise ValueError("Review the receipt and confirm all details first")
    extracted = json.loads(draft["extracted"])
    if (
        extracted.get("receipt_format") == WAVE_CHANNEL_FORMAT
        and account["kind"].lower() != "channel"
    ):
        raise ValueError("Select a WavePay Channel wallet for this receipt")
    return extracted


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


def masked_phone_from_draft(extracted):
    """Use stored extraction rather than trusting the read-only browser input."""
    contact = extracted.get("masked_phone", "")
    if isinstance(contact, str) and re.fullmatch(r"[*•xX]{2,}\d{3,}", contact):
        return contact
    return None
