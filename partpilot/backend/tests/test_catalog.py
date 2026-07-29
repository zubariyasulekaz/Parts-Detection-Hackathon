"""Tests for the /products endpoints.

Exercises the API layer (routing, validation, error-to-status mapping)
through a `dependency_overrides` fake in place of `ProductService`, so
no live Postgres connection is required to run this suite. Once a test
database is wired up, extend this with real `ProductRepository`
integration tests.
"""

from datetime import UTC, datetime

import pytest
from fastapi.testclient import TestClient

from backend.api.dependencies import get_product_service
from backend.app import create_app
from backend.core.exceptions import ProductAlreadyExists, ProductNotFound
from backend.schemas.catalog import ProductCreate, ProductResponse, ProductUpdate


class FakeProductService:
    """In-memory stand-in for `ProductService`, used only in tests."""

    def __init__(self) -> None:
        self._products: dict[str, ProductResponse] = {}

    async def create_product(self, data: ProductCreate) -> ProductResponse:
        if data.sku in self._products:
            raise ProductAlreadyExists(f"Product with SKU '{data.sku}' already exists.")
        now = datetime.now(UTC)
        product = ProductResponse(**data.model_dump(), created_at=now, updated_at=now)
        self._products[data.sku] = product
        return product

    async def update_product(self, sku: str, data: ProductUpdate) -> ProductResponse:
        existing = self._products.get(sku)
        if existing is None:
            raise ProductNotFound(f"Product with SKU '{sku}' was not found.")
        updated = existing.model_copy(
            update={
                "updated_at": datetime.now(UTC),
                **data.model_dump(exclude_unset=True),
            }
        )
        self._products[sku] = updated
        return updated

    async def delete_product(self, sku: str) -> None:
        if sku not in self._products:
            raise ProductNotFound(f"Product with SKU '{sku}' was not found.")
        del self._products[sku]

    async def get_product(self, sku: str) -> ProductResponse:
        product = self._products.get(sku)
        if product is None:
            raise ProductNotFound(f"Product with SKU '{sku}' was not found.")
        return product

    async def list_products(self, limit: int = 50, offset: int = 0) -> list[ProductResponse]:
        return list(self._products.values())[offset : offset + limit]

    async def search_by_category(self, category: str, limit: int = 50) -> list[ProductResponse]:
        return [p for p in self._products.values() if p.category == category][:limit]

    async def search_by_brand(self, brand: str, limit: int = 50) -> list[ProductResponse]:
        return [p for p in self._products.values() if p.brand == brand][:limit]

    async def count(self) -> int:
        return len(self._products)


@pytest.fixture
def fake_service() -> FakeProductService:
    return FakeProductService()


@pytest.fixture
def client(fake_service: FakeProductService) -> TestClient:
    """Override the module-level `client` fixture with one wired to the fake service."""
    app = create_app()
    app.dependency_overrides[get_product_service] = lambda: fake_service
    return TestClient(app)


def _sample_payload(sku: str = "OF-001") -> dict:
    return {
        "sku": sku,
        "product_name": "Oil Filter",
        "brand": "Bosch",
        "category": "oil_filter",
        "description": "Standard spin-on oil filter.",
        "image_paths": ["images/OF-001/front.jpg"],
        "replacement_sku": None,
        "alternative_skus": [],
        "accessory_skus": [],
        "compatible_vehicles": [{"make": "Honda", "model": "City", "year": 2020}],
    }


def test_create_product(client: TestClient) -> None:
    response = client.post("/api/v1/products", json=_sample_payload())

    assert response.status_code == 201
    body = response.json()
    assert body["success"] is True
    assert body["data"]["sku"] == "OF-001"
    assert body["data"]["compatible_vehicles"] == [{"make": "Honda", "model": "City", "year": 2020}]


def test_create_product_rejects_empty_required_fields(client: TestClient) -> None:
    payload = _sample_payload()
    payload["brand"] = "   "

    response = client.post("/api/v1/products", json=payload)

    assert response.status_code == 422


def test_create_duplicate_sku_returns_conflict(client: TestClient) -> None:
    client.post("/api/v1/products", json=_sample_payload())

    response = client.post("/api/v1/products", json=_sample_payload())

    assert response.status_code == 409
    assert response.json()["error_code"] == "PRODUCT_ALREADY_EXISTS"


def test_get_product_returns_created_product(client: TestClient) -> None:
    client.post("/api/v1/products", json=_sample_payload())

    response = client.get("/api/v1/products/OF-001")

    assert response.status_code == 200
    assert response.json()["data"]["sku"] == "OF-001"


def test_get_unknown_product_returns_404(client: TestClient) -> None:
    response = client.get("/api/v1/products/UNKNOWN-SKU")

    assert response.status_code == 404
    assert response.json()["error_code"] == "PRODUCT_NOT_FOUND"


def test_update_product(client: TestClient) -> None:
    client.post("/api/v1/products", json=_sample_payload())

    response = client.put("/api/v1/products/OF-001", json={"brand": "Mann Filter"})

    assert response.status_code == 200
    assert response.json()["data"]["brand"] == "Mann Filter"


def test_delete_product(client: TestClient) -> None:
    client.post("/api/v1/products", json=_sample_payload())

    delete_response = client.delete("/api/v1/products/OF-001")
    assert delete_response.status_code == 200

    follow_up = client.get("/api/v1/products/OF-001")
    assert follow_up.status_code == 404


def test_list_products(client: TestClient) -> None:
    client.post("/api/v1/products", json=_sample_payload(sku="OF-001"))
    client.post("/api/v1/products", json=_sample_payload(sku="OF-002"))

    response = client.get("/api/v1/products")

    assert response.status_code == 200
    assert len(response.json()["data"]) == 2


def test_list_products_filtered_by_category(client: TestClient) -> None:
    client.post("/api/v1/products", json=_sample_payload(sku="OF-001"))
    other = _sample_payload(sku="BP-001")
    other["category"] = "brake_pad"
    client.post("/api/v1/products", json=other)

    response = client.get("/api/v1/products", params={"category": "brake_pad"})

    assert response.status_code == 200
    data = response.json()["data"]
    assert len(data) == 1
    assert data[0]["sku"] == "BP-001"


# TODO: Once a test database is wired up, add integration tests that
# exercise `ProductRepository`/`ProductService` directly against a real
# (or containerized) PostgreSQL instance, including uniqueness/rollback
# behavior that this fake-service suite cannot cover.
