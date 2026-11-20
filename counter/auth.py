"""Password verification, sessions and owner/staff permissions."""

import hashlib
import hmac
import secrets
import time
from http.cookies import SimpleCookie


def require_owner(user):
    if user["role"] != "owner":
        raise ValueError("Owner access required")


def hash_password(password, salt=None):
    salt = salt or secrets.token_hex(16)
    return (
        salt
        + ":"
        + hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), 200000).hex()
    )


def current_user(connection, cookie_header):
    cookie = SimpleCookie(cookie_header or "")
    token = cookie.get("ledger_session")
    return connection.execute(
        "SELECT u.id,u.name,u.role FROM users u JOIN sessions s ON s.user_id=u.id "
        "WHERE s.token=? AND s.expires>?",
        (token.value if token else "", time.time()),
    ).fetchone()


def sign_in(connection, data, setup=False):
    """Create the first owner if requested and issue a twelve-hour session."""
    name = str(data.get("name", "")).strip()
    password = str(data.get("password", ""))
    if setup:
        if connection.execute("SELECT 1 FROM users").fetchone():
            raise ValueError("Shop is already set up")
        if not name or len(password) < 10:
            raise ValueError("Choose a name and a password of at least 10 characters")
        connection.execute(
            "INSERT INTO users(name,password,role) VALUES(?,?,?)",
            (name, hash_password(password), "owner"),
        )
    user = connection.execute("SELECT * FROM users WHERE name=?", (name,)).fetchone()
    if not user or not hmac.compare_digest(
        user["password"], hash_password(password, user["password"].split(":")[0])
    ):
        raise ValueError("Incorrect name or password")
    token = secrets.token_urlsafe(32)
    connection.execute(
        "INSERT INTO sessions VALUES(?,?,?)", (token, user["id"], time.time() + 43200)
    )
    return token


def sign_out(connection, user):
    connection.execute("DELETE FROM sessions WHERE user_id=?", (user["id"],))
