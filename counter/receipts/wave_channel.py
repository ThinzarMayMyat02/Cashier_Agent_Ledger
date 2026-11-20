"""Wave Channel layout: customer principal differs from net wallet movement."""

import re

TRANSACTION_NUMBER_PATTERN = r"(?m)^\s*(\d{10})(?:\s+(?:[@©®G§&]+|8))?\s*$"


def is_channel_layout(is_cash_in, is_receive, header_amount_count):
    # Both verified Channel layouts show principal + commission before the date.
    return is_cash_in or (is_receive and header_amount_count == 2)


def parse_channel_receipt(amounts, header_text, receipt_time, is_cash_in):
    """Decode the verified row order; ambiguous rows stay editable for review."""
    identifiers = re.findall(TRANSACTION_NUMBER_PATTERN, header_text)
    total_amount = amounts[-1][0] if amounts and amounts[-1][0] > 0 else None
    wallet_delta = (
        -total_amount if amounts and amounts[-1][1] in ("-", "−") else total_amount
    )
    expected_row_count = 6 if is_cash_in else 5
    has_complete_layout = len(amounts) == expected_row_count and amounts[0][0] > 0
    principal = amounts[0][0] if has_complete_layout else None
    commission = amounts[1][0] if has_complete_layout else None
    provider_fee = _provider_fee(amounts, has_complete_layout, is_cash_in)
    amounts_consistent = _amounts_agree(
        amounts, principal, commission, provider_fee, wallet_delta, is_cash_in
    )
    has_unique_transaction = len(identifiers) == 2 or (
        not is_cash_in and len(identifiers) == 1
    )
    return dict(
        receipt_format="wave_channel",
        account_kind="Channel",
        customer="",  # A reference number or masked NRC is not a customer name.
        phone=identifiers[0] if is_cash_in and len(identifiers) == 2 else "",
        masked_phone="",
        provider_transaction_id=identifiers[-1] if has_unique_transaction else "",
        receipt_time=receipt_time,
        transaction_type=(
            ("cash_in" if is_cash_in else "cash_out") if amounts_consistent else ""
        ),
        receipt_principal=principal,
        total_amount=total_amount,
        provider_commission=commission,
        provider_fee=provider_fee,
        receipt_wallet_delta=wallet_delta,
        channel_amounts_consistent=amounts_consistent,
    )


def _provider_fee(amounts, has_complete_layout, is_cash_in):
    if not is_cash_in and has_complete_layout:
        return amounts[-2][0]
    return amounts[-3][0] if len(amounts) >= 6 else None


def _amounts_agree(
    amounts, principal, commission, provider_fee, wallet_delta, is_cash_in
):
    if None in (principal, commission, provider_fee):
        return False
    principal_delta = -principal if is_cash_in else principal
    expected_wallet_delta = principal_delta + commission - provider_fee
    repeated_principal = amounts[2][0]
    repeated_commission_matches = not is_cash_in or amounts[-2][0] == commission
    signs_agree = not any(
        (sign == "+" and is_cash_in) or (sign in ("-", "−") and not is_cash_in)
        for _, sign in amounts
    )
    return (
        expected_wallet_delta == wallet_delta
        and repeated_principal == principal
        and repeated_commission_matches
        and signs_agree
    )
