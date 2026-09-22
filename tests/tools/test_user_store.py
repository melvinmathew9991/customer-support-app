"""Contract tests: MockUserStore and SqliteUserStore must behave identically, since
`agents/support.py` is meant to work unchanged with either one (Phase 7,
docs/User-Store-Design.md)."""
import sqlite3
import threading

import pytest

from customer_support_app.tools.user_store import MockUserStore, SqliteUserStore


@pytest.fixture(params=["mock", "sqlite"])
def store(request, tmp_path):
    if request.param == "mock":
        return MockUserStore()
    return SqliteUserStore(tmp_path / "users.sqlite")


def _ids(store, query):
    return [user["user_id"] for user in store.search_user_info(query)]


@pytest.mark.parametrize(
    "query",
    [
        "michaeljackson@gmail.com",
        "MichaelJackson@Gmail.com",
        "  michaeljackson@gmail.com ",
    ],
)
def test_email_lookup_ignores_case_and_surrounding_space(store, query):
    assert _ids(store, query) == ["1"]


@pytest.mark.parametrize(
    "query",
    ["0452 333 667", "0452333667", "0452-333-667", "(0452) 333 667", "my number is 0452 333 667"],
)
def test_phone_lookup_ignores_spacing_and_punctuation(store, query):
    assert _ids(store, query) == ["2"]


@pytest.mark.parametrize(
    "query",
    ["nobody@nowhere.com", "0452 999 999", "12345", "what's up", "", "   "],
)
def test_unknown_or_too_short_input_matches_nobody(store, query):
    assert _ids(store, query) == []


def test_a_bare_digit_run_shorter_than_a_phone_number_never_matches(store):
    # "1" is a valid user_id, and the subscription lookup is keyed by it, but the
    # identity lookup must never resolve a person from a fragment.
    assert _ids(store, "1") == []


def test_subscription_lookup(store):
    assert store.search_user_subscription("1") == [{"user_id": "1", "subscription": "premium"}]
    assert store.search_user_subscription("4") == []


def test_sqlite_store_does_not_duplicate_rows_on_reopen(tmp_path):
    db_path = tmp_path / "users.sqlite"
    SqliteUserStore(db_path)
    store = SqliteUserStore(db_path)
    assert _ids(store, "michaeljackson@gmail.com") == ["1"]


def test_sqlite_store_seeds_safely_when_opened_concurrently(tmp_path):
    # Two stores racing to seed the same brand-new file must not crash with a
    # PRIMARY KEY collision (INSERT OR IGNORE, not a COUNT-then-INSERT guard alone).
    db_path = tmp_path / "users.sqlite"
    errors = []

    def _open():
        try:
            SqliteUserStore(db_path)
        except Exception as error:  # noqa: BLE001 - the test's whole point is "did anything raise"
            errors.append(error)

    threads = [threading.Thread(target=_open) for _ in range(8)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()

    assert errors == []
    store = SqliteUserStore(db_path)
    assert _ids(store, "michaeljackson@gmail.com") == ["1"]
    with sqlite3.connect(db_path) as conn:
        assert conn.execute("SELECT COUNT(*) FROM users").fetchone()[0] == 4


def test_sqlite_store_creates_its_parent_directory(tmp_path):
    db_path = tmp_path / "nested" / "dir" / "users.sqlite"
    store = SqliteUserStore(db_path)
    assert db_path.exists()
    assert _ids(store, "michaeljackson@gmail.com") == ["1"]
