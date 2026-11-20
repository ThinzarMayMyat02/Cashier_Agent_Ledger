-- Base tables. Existing ledgers are extended by database.initialize().
CREATE TABLE IF NOT EXISTS users(
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL UNIQUE,
    password TEXT NOT NULL,
    role TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS sessions (
    token TEXT PRIMARY KEY,
    user_id INTEGER REFERENCES users(id),
    expires REAL
);
CREATE TABLE IF NOT EXISTS accounts (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    provider TEXT NOT NULL,
    kind TEXT NOT NULL,
    phone TEXT NOT NULL DEFAULT '',
    opening INTEGER NOT NULL DEFAULT 0,
    active INTEGER NOT NULL DEFAULT 1
);
CREATE TABLE IF NOT EXISTS entries (
    id TEXT PRIMARY KEY,
    type TEXT NOT NULL,
    account_id INTEGER REFERENCES accounts(id),
    amount INTEGER NOT NULL,
    fee INTEGER NOT NULL DEFAULT 0,
    cash_delta INTEGER NOT NULL,
    wallet_delta INTEGER NOT NULL,
    phone TEXT NOT NULL DEFAULT '',
    customer TEXT NOT NULL DEFAULT '',
    note TEXT NOT NULL DEFAULT '',
    staff INTEGER NOT NULL REFERENCES users(id),
    created TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now')),
    reversed INTEGER NOT NULL DEFAULT 0,
    reverse_staff INTEGER,
    reverse_note TEXT
);
CREATE TABLE IF NOT EXISTS closings (
    id INTEGER PRIMARY KEY,
    staff INTEGER REFERENCES users(id),
    created TEXT DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now')),
    snapshot TEXT NOT NULL
);
