"""Owner-managed staff creation."""

from .auth import require_owner, hash_password


def create_staff(connection, user, data):
    """Validate and write within the caller-owned BEGIN IMMEDIATE transaction."""
    require_owner(user)
    if len(data.get("password", "")) < 10 or not data.get("name", "").strip():
        raise ValueError("Name and password of at least 10 characters required")
    connection.execute(
        "INSERT INTO users(name,password,role) VALUES(?,?,?)",
        (data["name"].strip(), hash_password(data["password"]), "staff"),
    )
