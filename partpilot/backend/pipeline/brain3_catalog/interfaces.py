"""Abstract interfaces for Brain 3 (Catalog Intelligence).

Downstream code should depend on `CatalogInterface`, not the concrete
`CatalogService` implementation.
"""

from abc import ABC, abstractmethod

from backend.schemas.catalog import Product
from backend.schemas.recommendation import Recommendation


class CatalogInterface(ABC):
    """Contract for reading catalog metadata."""

    @abstractmethod
    def get_product(self, sku: str) -> Product:
        """Fetch full catalog metadata for a single SKU.

        Raises:
            backend.core.exceptions.CatalogError: If the SKU is unknown
                or the catalog cannot be read.
        """
        raise NotImplementedError

    @abstractmethod
    def search_by_category(self, category: str, limit: int = 50) -> list[Product]:
        """List products belonging to a given category.

        Args:
            category: Product category, as predicted by Brain 1.
            limit: Maximum number of products to return.
        """
        raise NotImplementedError


class RecommendationInterface(ABC):
    """Contract for producing alternative/accessory recommendations."""

    @abstractmethod
    def recommend(self, sku: str) -> Recommendation:
        """Return alternative and accessory products related to `sku`.

        Raises:
            backend.core.exceptions.CatalogError: If the SKU is unknown.
        """
        raise NotImplementedError
