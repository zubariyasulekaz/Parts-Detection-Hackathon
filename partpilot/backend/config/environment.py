"""Environment helpers built on top of `Settings`.

Keeps environment-branching logic (e.g. "are we in production?") out of
business logic modules.
"""

from enum import StrEnum
from functools import lru_cache

from backend.config.settings import get_settings


class Environment(StrEnum):
    """Supported deployment environments."""

    DEVELOPMENT = "development"
    TESTING = "testing"
    STAGING = "staging"
    PRODUCTION = "production"


@lru_cache
def get_environment() -> Environment:
    """Return the current `Environment` derived from settings."""
    return Environment(get_settings().ENV)


def is_production() -> bool:
    """Return True if the app is running in production."""
    return get_environment() is Environment.PRODUCTION


def is_development() -> bool:
    """Return True if the app is running in development."""
    return get_environment() is Environment.DEVELOPMENT


def is_testing() -> bool:
    """Return True if the app is running under the test suite."""
    return get_environment() is Environment.TESTING
