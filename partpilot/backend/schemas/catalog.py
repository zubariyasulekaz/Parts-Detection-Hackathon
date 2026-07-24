"""Schemas describing catalog entries (Brain 3 output)."""

from backend.schemas.common import APIModel


class Product(APIModel):
    """A single catalog product record."""

    sku: str
    product_name: str
    brand: str
    category: str
    description: str
    compatible_vehicles: list[str] = []
    replacement_sku: str | None = None
    alternative_sku: str | None = None
    accessory_skus: list[str] = []
