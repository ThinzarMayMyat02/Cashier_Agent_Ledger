"""Business-date summaries derived from the posted wallet ledger."""

import json
from datetime import date
from . import clock


def daily_report(connection, business_date, account_id=None):
    try:
        selected = date.fromisoformat(business_date)
    except (ValueError, TypeError):
        raise ValueError("Choose a valid report date")
    if selected.isoformat() != business_date or business_date > clock.business_day():
        raise ValueError("Choose today or an earlier report date")
    accounts = connection.execute("SELECT * FROM accounts ORDER BY id").fetchall()
    if account_id:
        accounts = [account for account in accounts if str(account["id"]) == account_id]
        if not accounts:
            raise ValueError("Account not found")
    entries = connection.execute(
        """
        SELECT e.*, original.type AS original_type
        FROM entries e LEFT JOIN entries original ON original.id=e.reversal_of
        WHERE e.reversed<>1
    """
    ).fetchall()
    wallets = []
    for account in accounts:
        related = [entry for entry in entries if entry["account_id"] == account["id"]]
        opening = account["opening"] + sum(
            entry["wallet_delta"]
            for entry in related
            if entry["business_date"] < business_date
        )
        daily = [entry for entry in related if entry["business_date"] == business_date]
        movement = sum(entry["wallet_delta"] for entry in daily)

        def amount(kind):
            return sum(
                entry["amount"]
                for entry in daily
                if (entry["original_type"] or entry["type"]) == kind
            )

        wallets.append(
            dict(
                id=account["id"],
                name=account["name"],
                provider=account["provider"],
                active=bool(account["active"]),
                opening=opening,
                movement=movement,
                closing=opening + movement,
                cash_in=amount("cash_in"),
                cash_out=amount("cash_out"),
                fees=sum(
                    (
                        entry["collected_fee"]
                        if entry["collected_fee"] is not None
                        else entry["fee"]
                    )
                    for entry in daily
                ),
                transactions=sum(
                    entry["type"] in ("cash_in", "cash_out") for entry in daily
                ),
                provider_commission=sum(
                    entry["provider_commission"] for entry in daily
                ),
                provider_fee=sum(entry["provider_fee"] for entry in daily),
                reversals=sum(entry["type"] == "reversal" for entry in daily),
            )
        )
    totals = {
        key: sum(wallet[key] for wallet in wallets)
        for key in (
            "opening",
            "movement",
            "closing",
            "cash_in",
            "cash_out",
            "fees",
            "provider_commission",
            "provider_fee",
            "transactions",
            "reversals",
        )
    }
    closing = connection.execute(
        "SELECT snapshot FROM closings WHERE business_date=?", (business_date,)
    ).fetchone()
    return dict(
        business_date=business_date,
        accounts=wallets,
        totals=totals,
        closing=json.loads(closing["snapshot"]) if closing else None,
    )
