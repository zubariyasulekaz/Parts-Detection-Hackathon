"""Centralized logging configuration.

Every module in the codebase should obtain its logger via `get_logger(__name__)`
rather than calling `print` or configuring `logging` itself, so log format
and level stay consistent across the whole application.
"""

import logging
import sys
from logging import Logger

from backend.config.settings import get_settings

_LOG_FORMAT = "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"
_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"

_configured = False


def configure_logging() -> None:
    """Configure the root logger once, based on `Settings.LOG_LEVEL`.

    Safe to call multiple times; subsequent calls are no-ops. Should be
    invoked as early as possible in the application lifecycle (see
    `backend.core.startup`).
    """
    global _configured
    if _configured:
        return

    settings = get_settings()
    level = getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO)

    handler = logging.StreamHandler(stream=sys.stdout)
    handler.setFormatter(logging.Formatter(fmt=_LOG_FORMAT, datefmt=_DATE_FORMAT))

    root_logger = logging.getLogger()
    root_logger.setLevel(level)
    root_logger.handlers.clear()
    root_logger.addHandler(handler)

    _configured = True


def get_logger(name: str) -> Logger:
    """Return a module-level logger, ensuring logging is configured first.

    Args:
        name: Typically `__name__` of the calling module.

    Returns:
        A configured standard-library `Logger` instance.
    """
    configure_logging()
    return logging.getLogger(name)
