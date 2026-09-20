import pytest

from customer_support_app.tools.user_info_db import (
    search_user_info_on_db,
    search_user_subscription_on_db,
)


def _ids(query):
    return [user["user_id"] for user in search_user_info_on_db.invoke(query)]


@pytest.mark.parametrize(
    "query",
    [
        "michaeljackson@gmail.com",
        "MichaelJackson@Gmail.com",
        "  michaeljackson@gmail.com ",
    ],
)
def test_email_lookup_ignores_case_and_surrounding_space(query):
    assert _ids(query) == ["1"]


@pytest.mark.parametrize(
    "query",
    ["0452 333 667", "0452333667", "0452-333-667", "(0452) 333 667", "my number is 0452 333 667"],
)
def test_phone_lookup_ignores_spacing_and_punctuation(query):
    assert _ids(query) == ["2"]


@pytest.mark.parametrize(
    "query",
    ["nobody@nowhere.com", "0452 999 999", "12345", "what's up", "", "   "],
)
def test_unknown_or_too_short_input_matches_nobody(query):
    assert _ids(query) == []


def test_a_bare_digit_run_shorter_than_a_phone_number_never_matches():
    # "1" is a valid user_id, and the subscription tool is keyed by it, but the
    # identity lookup must never resolve a person from a fragment.
    assert _ids("1") == []


def test_subscription_lookup_is_unchanged():
    assert search_user_subscription_on_db.invoke("1") == [
        {"user_id": "1", "subscription": "premium"}
    ]
    assert search_user_subscription_on_db.invoke("4") == []
