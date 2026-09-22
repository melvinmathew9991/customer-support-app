"""Contract tests: MockUserStore and SqliteUserStore must behave identically, since
`agents/support.py` is meant to work unchanged with either one (Phase 7,
docs/User-Store-Design.md)."""
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


def test_sqlite_store_creates_its_parent_directory(tmp_path):
    db_path = tmp_path / "nested" / "dir" / "users.sqlite"
    store = SqliteUserStore(db_path)
    assert db_path.exists()
    assert _ids(store, "michaeljackson@gmail.com") == ["1"]
