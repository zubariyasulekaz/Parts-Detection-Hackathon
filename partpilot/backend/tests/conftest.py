"""Shared pytest fixtures for the backend test suite."""

import pytest
from fastapi.testclient import TestClient

from backend.app import create_app


@pytest.fixture
def client() -> TestClient:
    """Return a `TestClient` wrapping a freshly constructed FastAPI app."""
    return TestClient(create_app())
