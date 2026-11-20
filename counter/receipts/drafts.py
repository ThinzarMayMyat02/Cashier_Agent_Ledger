"""Private receipt drafts; extraction never changes ledger balances."""

import json
import secrets
import time


DRAFT_LIFETIME_SECONDS = 86400


def save_draft(connection, user, provider, image, extracted):
    import_id = secrets.token_urlsafe(24)
    connection.execute(
        "DELETE FROM receipt_imports WHERE entry_id IS NULL AND created<?",
        (time.time() - DRAFT_LIFETIME_SECONDS,),
    )
    connection.execute(
        "INSERT INTO receipt_imports VALUES(?,?,?,?,?,?,NULL)",
        (import_id, user["id"], provider, image, json.dumps(extracted), time.time()),
    )
    return dict(extracted, import_id=import_id)
