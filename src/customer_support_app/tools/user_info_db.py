import re

from langchain_core.tools import tool

user_sub = [
    {"user_id": "1", "subscription": "premium"},
    {"user_id": "2", "subscription": "free"},
    {"user_id": "3", "subscription": "premium"},
]
user_info = [
    {
        "name": "Michael Jackson",
        "email": "michaeljackson@gmail.com",
        "user_id": "1",
        "phone": "0452 333 666",
        "language": "English",
    },
    {
        "name": "John Doe",
        "email": "john@doe.com",
        "user_id": "2",
        "phone": "0452 333 667",
        "language": "Spanish",
    },
    {
        "name": "Carl Sagan",
        "email": "carl@sagan.com",
        "user_id": "3",
        "phone": "0452 333 668",
        "language": "Italian",
    },
    {
        "name": "XYZ",
        "email": "xyz@gmail.com",
        "user_id": "4",
        "phone": "123456789",
        "language": "Italian",
    },
]


# Fewer digits than this is not a phone number worth matching on.
_MIN_PHONE_DIGITS = 6


def _digits(text: str) -> str:
    return re.sub(r"\D", "", text)


@tool("user_info_db", return_direct=True)
def search_user_info_on_db(email: str):
    """Searches users by email address (any letter case) or phone number (any spacing)"""
    query = email.strip()
    if "@" in query:
        return [user for user in user_info if user["email"].lower() == query.lower()]
    digits = _digits(query)
    if len(digits) >= _MIN_PHONE_DIGITS:
        return [user for user in user_info if _digits(user["phone"]) == digits]
    return []


@tool("user_subscription_db", return_direct=True)
def search_user_subscription_on_db(id: str):
    """Searches users subscription by user id"""
    return list(filter(lambda user: user["user_id"] == id, user_sub))
