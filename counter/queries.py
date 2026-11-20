"""Read models shared by API responses and balance validation."""

from . import clock


def get_shop_state(connection, user):
    """Build one consistent API snapshot; flags 0/2 count, legacy flag 1 does not."""
    accounts = [
        dict(r)
        for r in connection.execute(
            "SELECT a.*,a.opening+COALESCE((SELECT SUM(wallet_delta) FROM entries e WHERE e.account_id=a.id AND e.reversed<>1),0) balance FROM accounts a"
        )
    ]
    entries = [
        dict(r)
        for r in connection.execute(
            "SELECT e.*,u.name staff_name,a.name account_name FROM entries e JOIN users u ON e.staff=u.id LEFT JOIN accounts a ON a.id=e.account_id ORDER BY e.created DESC,e.rowid DESC"
        )
    ]
    for entry in entries:
        entry["recorded_fee"] = entry["fee"]
        entry["fee_review_required"] = (
            entry["type"] in ["cash_in", "cash_out"] and entry["collected_fee"] is None
        )
        if entry["collected_fee"] is not None:
            entry["fee"] = entry["collected_fee"]
        entry["reversed"] = bool(entry["reversed"])
    return dict(
        business_date=clock.business_day(),
        user=dict(user),
        accounts=accounts,
        entries=entries,
        cash=connection.execute(
            "SELECT COALESCE(SUM(cash_delta),0) FROM entries WHERE reversed<>1"
        ).fetchone()[0],
        staff=(
            [dict(r) for r in connection.execute("SELECT id,name,role FROM users")]
            if user["role"] == "owner"
            else []
        ),
        closings=[
            dict(r)
            for r in connection.execute(
                "SELECT c.*,u.name staff_name FROM closings c JOIN users u ON c.staff=u.id ORDER BY c.id DESC LIMIT 30"
            )
        ],
    )
