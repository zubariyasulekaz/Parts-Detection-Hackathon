"""Tests for the /catalog endpoints.

Only exercises the dummy placeholder responses — once Brain 3 is
implemented, extend this with real catalog fixtures and assertions.
"""

from fastapi.testclient import TestClient


def test_get_product_returns_dummy_response(client: TestClient) -> None:
    response = client.get("/api/v1/catalog/SOME-SKU-123")

    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert body["data"]["sku"] == "SOME-SKU-123"


def test_get_recommendations_returns_dummy_response(client: TestClient) -> None:
    response = client.get("/api/v1/catalog/SOME-SKU-123/recommendations")

    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert body["data"]["alternatives"] == []
    assert body["data"]["accessories"] == []


# TODO: Once Brain 3 is implemented, add tests covering:
#   - 404 for unknown SKUs (CatalogError).
#   - Real alternative/accessory resolution for known fixtures.
