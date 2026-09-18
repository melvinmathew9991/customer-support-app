import pytest

from customer_support_app.config import get_settings


@pytest.fixture(autouse=True)
def _clear_settings_cache():
    """get_settings() is lru_cached - clear it around each test so tests that
    construct their own Settings() don't leak into other tests."""
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()
