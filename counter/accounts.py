"""Account setup, opening funds and archival."""

import secrets
from . import clock
from .auth import require_owner
from .closing import require_open_day
from .fees import whole_amount
from .queries import get_shop_state


def save_account(connection, user, data):
    """Validate and write within the caller-owned BEGIN IMMEDIATE transaction."""
    require_owner(user)
    require_open_day(connection)
    name = str(data.get("name", "")).strip()
    provider = str(data.get("provider", "")).strip()
    kind = str(data.get("kind", "")).strip()
    if not name or not provider or (not kind):
        raise ValueError("Name, provider and account type are required")
    if data.get("id"):
        existing = connection.execute(
            "SELECT * FROM accounts WHERE id=?", (data["id"],)
        ).fetchone()
        if not existing:
            raise ValueError("Account missing")
        if not data.get("active", True):
            current = get_shop_state(connection, user)
            if (
                next(
                    (
                        account["balance"]
                        for account in current["accounts"]
                        if account["id"] == existing["id"]
                    )
                )
                != 0
            ):
                raise ValueError("Remove or transfer remaining funds before archiving")
        connection.execute(
            "UPDATE accounts SET name=?,provider=?,kind=?,phone=?,active=? WHERE id=?",
            (
                name,
                provider,
                kind,
                str(data.get("phone", "")),
                int(bool(data.get("active", True))),
                int(data["id"]),
            ),
        )
    else:
        opening = whole_amount(data.get("opening", 0))
        if opening < 0:
            raise ValueError("Opening balance cannot be negative")
        result = connection.execute(
            "INSERT INTO accounts(name,provider,kind,phone,opening) VALUES(?,?,?,?,0)",
            (name, provider, kind, str(data.get("phone", ""))),
        )
        if opening:
            connection.execute(
                "INSERT INTO entries(id,type,account_id,amount,cash_delta,wallet_delta,note,staff,business_date) VALUES(?,?,?,?,0,?,?,?,?)",
                (
                    secrets.token_hex(16),
                    "funds_in",
                    result.lastrowid,
                    opening,
                    opening,
                    "Opening funds",
                    user["id"],
                    clock.business_day(),
                ),
            )
