"""The user-lookup interface `agents/support.py`'s identification edge calls through,
plus an in-memory mock and a SQLite-backed real store (Sprint 4, Phase 7,
docs/User-Store-Design.md).

Both implementations read the same fixture data below, so a mock and a real answer can
never silently diverge - there is exactly one place the four sample users are defined.
Matching stays in Python (not SQL) on purpose: the table is a handful of rows, and doing
it here means there is only one place the matching rule (case-insensitive email, digits-only
phone) can be wrong, not two.
"""
import re
import sqlite3
from pathlib import Path
from typing import Protocol

# Fewer digits than this is not a phone number worth matching on.
_MIN_PHONE_DIGITS = 6

USERS = [
    {
        "user_id": "1",
        "name": "Michael Jackson",
        "email": "michaeljackson@gmail.com",
        "phone": "0452 333 666",
        "language": "English",
    },
    {
        "user_id": "2",
        "name": "John Doe",
        "email": "john@doe.com",
        "phone": "0452 333 667",
        "language": "Spanish",
    },
    {
        "user_id": "3",
        "name": "Carl Sagan",
        "email": "carl@sagan.com",
        "phone": "0452 333 668",
        "language": "Italian",
    },
    {
        "user_id": "4",
        "name": "XYZ",
        "email": "xyz@gmail.com",
        "phone": "123456789",
        "language": "Italian",
    },
]
SUBSCRIPTIONS = [
    {"user_id": "1", "subscription": "premium"},
    {"user_id": "2", "subscription": "free"},
    {"user_id": "3", "subscription": "premium"},
]


def _digits(text: str) -> str:
    return re.sub(r"\D", "", text)


def _matching_users(users: list[dict], query: str) -> list[dict]:
    """Searches users by email address (any letter case) or phone number (any spacing)."""
    query = query.strip()
    if "@" in query:
        return [user for user in users if user["email"].lower() == query.lower()]
    digits = _digits(query)
    if len(digits) >= _MIN_PHONE_DIGITS:
        return [user for user in users if _digits(user["phone"]) == digits]
    return []


class UserStore(Protocol):
    def search_user_info(self, query: str) -> list[dict]: ...
    def search_user_subscription(self, user_id: str) -> list[dict]: ...


class MockUserStore:
    """In-memory store over the fixture data above. The default for `UserInfoChainBasedEdge`
    and every existing test, and the deterministic fixture for tests going forward."""

    def __init__(self):
        self._users = USERS
        self._subscriptions = SUBSCRIPTIONS

    def search_user_info(self, query: str) -> list[dict]:
        return _matching_users(self._users, query)

    def search_user_subscription(self, user_id: str) -> list[dict]:
        return [sub for sub in self._subscriptions if sub["user_id"] == user_id]


class SqliteUserStore:
    """SQLite-backed store, standard library only. Auto-seeds the fixture data into a fresh
    or empty database the first time it's opened, so there's no separate seed step to run
    or forget - the same self-healing-on-open posture as `session_store.SessionStore`."""

    def __init__(self, db_path: Path):
        db_path.parent.mkdir(parents=True, exist_ok=True)
        self._db_path = db_path
        self._init_db()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self._db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self) -> None:
        with self._connect() as conn:
            conn.execute(
                "CREATE TABLE IF NOT EXISTS users ("
                "user_id TEXT PRIMARY KEY, name TEXT NOT NULL, email TEXT NOT NULL, "
                "phone TEXT NOT NULL, language TEXT NOT NULL)"
            )
            conn.execute(
                "CREATE TABLE IF NOT EXISTS subscriptions ("
                "user_id TEXT PRIMARY KEY, subscription TEXT NOT NULL)"
            )
            if conn.execute("SELECT COUNT(*) FROM users").fetchone()[0] == 0:
                conn.executemany(
                    "INSERT INTO users (user_id, name, email, phone, language) "
                    "VALUES (:user_id, :name, :email, :phone, :language)",
                    USERS,
                )
                conn.executemany(
                    "INSERT INTO subscriptions (user_id, subscription) "
                    "VALUES (:user_id, :subscription)",
                    SUBSCRIPTIONS,
                )

    def search_user_info(self, query: str) -> list[dict]:
        with self._connect() as conn:
            rows = [
                dict(row)
                for row in conn.execute(
                    "SELECT user_id, name, email, phone, language FROM users"
                ).fetchall()
            ]
        return _matching_users(rows, query)

    def search_user_subscription(self, user_id: str) -> list[dict]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT user_id, subscription FROM subscriptions WHERE user_id = ?",
                (user_id,),
            ).fetchall()
        return [dict(row) for row in rows]
