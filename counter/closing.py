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
    """Save a reviewed reconciliation within the caller-owned serialized transaction."""
    require_open_day(connection)
    snapshot = get_shop_state(connection, user)
    counts = data.get("counts", {})
    expected = {
        "cash": snapshot["cash"],
        **{str(a["id"]): a["balance"] for a in snapshot["accounts"]},
    }
    if (
        not isinstance(counts, dict)
        or set(counts) != set(expected)
        or any((type(v) != int or v < 0 for v in counts.values()))
    ):
        raise ValueError("Enter a nonnegative count for cash and every wallet")
    mode = data.get("closing_mode", "strict")
    if mode not in ("strict", "allow_variance"):
        raise ValueError("Invalid closing mode")
    note_value = data.get("note", "")
    note = note_value.strip() if isinstance(note_value, str) else ""
    if len(note) > 500:
        raise ValueError("Closing note must be 500 characters or fewer")
    has_difference = counts != expected
    if has_difference and mode == "strict":
        raise ValueError("Resolve all balance differences before closing")
    if has_difference and not note:
        raise ValueError("Add a note explaining the closing differences")
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
                    "note": note,
                    "closing_mode": mode,
                    "status": "variance" if has_difference else "matched",
                    "differences": {
                        key: counts[key] - value for key, value in expected.items()
                    },
                }
            ),
            clock.business_day(),
        ),
    )
