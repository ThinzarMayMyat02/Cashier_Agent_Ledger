"""Posting orchestration: validate, calculate, check balances, then persist once."""

from dataclasses import replace
from . import clock
from .closing import require_open_day
from .fees import whole_amount, prepare_posting_amounts
from .queries import get_shop_state
from .receipts.posting import (
    validate_receipt_review,
    validate_masked_phone,
    validate_provider_adjustments,
)

TRANSACTION_TYPES = ("cash_in", "cash_out")
FUNDING_TYPES = ("funds_in", "funds_out")
ENTRY_TYPES = (*TRANSACTION_TYPES, *FUNDING_TYPES, "expense")


def post_entry(connection, user, data):
    """Run inside Handler.write_command's BEGIN IMMEDIATE; never commit here."""
    require_open_day(connection)
    entry_type = data.get("type")
    amount = whole_amount(data.get("amount", 0), 1)
    account_value = data.get("account_id")
    account_id = (
        whole_amount(account_value, 1) if account_value not in (None, "") else None
    )
    if entry_type not in ENTRY_TYPES:
        raise ValueError("Invalid transaction type")
    customer = _validate_customer_name(data.get("customer", ""), entry_type)
    if entry_type in FUNDING_TYPES and user["role"] != "owner":
        raise ValueError("Owner access required")
    account = _find_active_account(connection, account_id, entry_type)
    provider_id = str(data.get("provider_transaction_id", "")).strip()
    if len(provider_id) > 80 or any(ord(character) < 32 for character in provider_id):
        raise ValueError("Invalid provider transaction ID")
    extracted = validate_receipt_review(data, account, entry_type)
    _ensure_unique_provider_reference(connection, account_id, provider_id)

    posting = prepare_posting_amounts(data, entry_type, amount, account_id)
    adjustments = validate_provider_adjustments(data, extracted, entry_type, amount)
    posting = replace(
        posting, wallet_delta=posting.wallet_delta + adjustments.wallet_delta
    )
    _ensure_sufficient_balances(get_shop_state(connection, user), account_id, posting)

    entry_id = str(data.get("id", ""))
    if not entry_id or len(entry_id) > 80:
        raise ValueError("Missing transaction identifier")
    receipt_time = str(data.get("receipt_time", "")).strip()
    if len(receipt_time) > 80:
        raise ValueError("Invalid receipt time")
    record = dict(
        id=entry_id,
        type=entry_type,
        account_id=account_id,
        amount=amount,
        fee=posting.collected_fee,
        cash_delta=posting.cash_delta,
        wallet_delta=posting.wallet_delta,
        phone=str(data.get("phone", ""))[:50],
        customer=customer,
        note=str(data.get("note", ""))[:500],
        staff=user["id"],
        accounting_rule="AGENT_CASH_V1",
        provider_commission=adjustments.commission,
        provider_fee=adjustments.fee,
        receipt_format=extracted.get("receipt_format"),
        customer_phone_masked=validate_masked_phone(extracted),
        provider_transaction_id=provider_id or None,
        receipt_time=receipt_time,
        suggested_fee=posting.suggested_fee,
        collected_fee=posting.collected_fee,
        fee_mode=posting.fee_mode,
        override_reason=posting.override_reason[:500],
        business_date=clock.business_day(),
    )
    _save_entry(connection, record)


def _validate_customer_name(value, entry_type):
    customer = value.strip() if isinstance(value, str) else ""
    if entry_type in TRANSACTION_TYPES and not customer:
        raise ValueError("Customer name is required")
    if len(customer) > 100 or any(ord(character) < 32 for character in customer):
        raise ValueError("Enter a valid customer name up to 100 characters")
    return customer


def _find_active_account(connection, account_id, entry_type):
    account = (
        connection.execute(
            "SELECT * FROM accounts WHERE id=? AND active=1", (account_id,)
        ).fetchone()
        if account_id
        else None
    )
    if (account_id or entry_type in TRANSACTION_TYPES) and not account:
        raise ValueError("Choose an active wallet account")
    return account


def _ensure_unique_provider_reference(connection, account_id, provider_id):
    if (
        provider_id
        and connection.execute(
            "SELECT 1 FROM entries WHERE account_id=? AND provider_transaction_id=? AND reversal_of IS NULL",
            (account_id, provider_id),
        ).fetchone()
    ):
        raise ValueError(
            "This provider transaction ID is already recorded for this account"
        )


def _ensure_sufficient_balances(state, account_id, posting):
    if state["cash"] + posting.cash_delta < 0:
        raise ValueError(
            f"Insufficient shop cash. Available: {state['cash']:,} MMK; required: {-posting.cash_delta:,} MMK."
        )
    if account_id:
        wallet_balance = next(
            account["balance"]
            for account in state["accounts"]
            if account["id"] == account_id
        )
        if wallet_balance + posting.wallet_delta < 0:
            raise ValueError("Insufficient wallet balance. Owner can add funds.")


def _save_entry(connection, record):
    """Persist the confirmed transaction and monetary audit fields only."""
    connection.execute(
        """INSERT INTO entries (
            id,type,account_id,amount,fee,cash_delta,wallet_delta,phone,customer,note,staff,
            accounting_rule,provider_commission,provider_fee,receipt_format,customer_phone_masked,
            provider_transaction_id,receipt_time,suggested_fee,collected_fee,
            fee_mode,override_reason,business_date
        ) VALUES (
            :id,:type,:account_id,:amount,:fee,:cash_delta,:wallet_delta,:phone,:customer,:note,:staff,
            :accounting_rule,:provider_commission,:provider_fee,:receipt_format,:customer_phone_masked,
            :provider_transaction_id,:receipt_time,:suggested_fee,:collected_fee,
            :fee_mode,:override_reason,:business_date
        )""",
        record,
    )
