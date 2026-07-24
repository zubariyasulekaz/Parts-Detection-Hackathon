"""Concrete `RecommendationInterface` implementation.

Produces alternative and accessory product recommendations for a given
SKU, based on catalog metadata (`replacement_sku`, `alternative_sku`,
`accessory_skus` fields).
"""

from backend.core.exceptions import CatalogError
from backend.core.logging import get_logger
from backend.pipeline.brain3_catalog.catalog_service import CatalogService
from backend.pipeline.brain3_catalog.interfaces import (
    CatalogInterface,
    RecommendationInterface,
)
from backend.schemas.catalog import Product
from backend.schemas.recommendation import Recommendation

logger = get_logger(__name__)


class RecommendationService(RecommendationInterface):
    """Builds alternative/accessory recommendations from catalog data."""

    def __init__(self, catalog: CatalogInterface | None = None) -> None:
        self._catalog = catalog or CatalogService()

    def _resolve_skus(self, skus: list[str]) -> list[Product]:
        """Resolve SKUs to `Product` records, skipping any that are unknown."""
        products: list[Product] = []
        for sku in skus:
            try:
                products.append(self._catalog.get_product(sku))
            except CatalogError:
                logger.warning("Recommendation references unknown SKU %s; skipping", sku)
        return products

    def recommend(self, sku: str) -> Recommendation:
        """Return alternative and accessory products related to `sku`.

        Alternatives are drawn from the product's ``replacement_sku`` and
        ``alternative_sku`` fields; accessories from ``accessory_skus``.
        Referenced SKUs that are missing from the catalog are skipped.

        Raises:
            backend.core.exceptions.CatalogError: If `sku` itself is unknown.
        """
        product = self._catalog.get_product(sku)

        # Preserve order (replacement first) while de-duplicating and excluding
        # the product itself.
        alternative_skus: list[str] = []
        for candidate in (product.replacement_sku, product.alternative_sku):
            if candidate and candidate != sku and candidate not in alternative_skus:
                alternative_skus.append(candidate)

        return Recommendation(
            alternatives=self._resolve_skus(alternative_skus),
            accessories=self._resolve_skus(product.accessory_skus),
        )
