"""Logging setup for entrypoints (CLI, Streamlit app).

Library modules should never call logging.basicConfig themselves - only an
entrypoint should configure the root logger, so importing this package as a
dependency doesn't clobber a host application's own logging setup.
"""
import logging

from customer_support_app.config import get_settings


def setup_logging() -> None:
    settings = get_settings()
    logging.basicConfig(
        level=settings.log_level,
        format="%(asctime)s %(levelname)-8s %(name)s: %(message)s",
    )
