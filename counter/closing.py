"""Daily reconciliation and posting cut-off checks."""

import json
from . import clock
from .queries import get_shop_state


def require_open_day(connection):
    if connection.execute(
        "SELECT 1 FROM closings WHERE business_date>=?", (clock.business_day(),)
    ).fetchone():
        raise ValueError("This business day is closed")


def close_day(connection, user, data):
    """Save a matching close within the caller-owned serialized transaction."""
    require_open_day(connection)
    snapshot = get_shop_state(connection, user)
    counts = data.get("counts", {})
    expected = {
        "cash": snapshot["cash"],
        **{str(a["id"]): a["balance"] for a in snapshot["accounts"]},
    }
    if set(counts) != set(expected) or any(
        (type(v) != int or v < 0 for v in counts.values())
    ):
        raise ValueError("Enter a nonnegative count for cash and every wallet")
    if counts != expected:
        raise ValueError("Resolve all balance differences before closing")
    if any(
        (e["fee_review_required"] and (not e["reversed"]) for e in snapshot["entries"])
    ):
        raise ValueError("Review historical cash and fee discrepancies before closing")
    connection.execute(
        "INSERT INTO closings(staff,snapshot,business_date) VALUES(?,?,?)",
        (
            user["id"],
            json.dumps(
                {
                    "expected": expected,
                    "counted": counts,
                    "note": str(data.get("note", ""))[:500],
                }
            ),
            clock.business_day(),
        ),
    )
