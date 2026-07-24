"""Schemas for alternative/accessory product recommendations (Brain 3)."""

from backend.schemas.catalog import Product
from backend.schemas.common import APIModel


class Recommendation(APIModel):
    """Alternative and accessory products related to a given SKU."""

    alternatives: list[Product] = []
    accessories: list[Product] = []
