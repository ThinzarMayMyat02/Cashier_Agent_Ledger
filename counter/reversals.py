"""Dated compensating entries linked to original records."""

import secrets
from . import clock
from .auth import require_owner
from .closing import require_open_day
from .queries import get_shop_state


def reverse_entry(connection, user, data):
    """Validate and write within the caller-owned BEGIN IMMEDIATE transaction."""
    require_owner(user)
    require_open_day(connection)
    reason = str(data.get("reason", "")).strip()
    if not reason:
        raise ValueError("A reversal reason is required")
    entry = connection.execute(
        "SELECT * FROM entries WHERE id=? AND reversed=0 AND reversal_of IS NULL",
        (data.get("id"),),
    ).fetchone()
    if not entry:
        raise ValueError("Record is already reversed or missing")
    current = get_shop_state(connection, user)
    if current["cash"] - entry["cash_delta"] < 0 or (
        entry["account_id"]
        and next(
            (
                item["balance"]
                for item in current["accounts"]
                if item["id"] == entry["account_id"]
            )
        )
        - entry["wallet_delta"]
        < 0
    ):
        raise ValueError(
            "Reversal would make a balance negative; review subsequent records first"
        )
    reversal_id = secrets.token_hex(16)
    connection.execute(
        "INSERT INTO entries(id,type,account_id,amount,fee,cash_delta,wallet_delta,note,staff,reversal_of,collected_fee,business_date) VALUES(?,?,?,?,?,?,?,?,?,?,?,?)",
        (
            reversal_id,
            "reversal",
            entry["account_id"],
            -entry["amount"],
            -entry["fee"],
            -entry["cash_delta"],
            -entry["wallet_delta"],
            reason[:500],
            user["id"],
            entry["id"],
            -entry["collected_fee"] if entry["collected_fee"] is not None else None,
            clock.business_day(),
        ),
    )
    connection.execute(
        "UPDATE entries SET provider_commission=?,provider_fee=?,receipt_format=?,accounting_rule=? WHERE id=?",
        (
            -entry["provider_commission"],
            -entry["provider_fee"],
            entry["receipt_format"],
            entry["accounting_rule"],
            reversal_id,
        ),
    )
    connection.execute(
        "UPDATE entries SET reversed=2,reverse_staff=?,reverse_note=? WHERE id=?",
        (user["id"], reason[:500], entry["id"]),
    )
