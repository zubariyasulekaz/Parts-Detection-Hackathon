"""Concrete `RecommendationInterface` implementation.

Produces alternative and accessory product recommendations for a given
SKU, based on catalog metadata (`replacement_sku`, `alternative_sku`,
`accessory_skus` fields).
"""

from backend.core.logging import get_logger
from backend.pipeline.brain3_catalog.catalog_service import CatalogService
from backend.pipeline.brain3_catalog.interfaces import (
    CatalogInterface,
    RecommendationInterface,
)
from backend.schemas.recommendation import Recommendation

logger = get_logger(__name__)


class RecommendationService(RecommendationInterface):
    """Builds alternative/accessory recommendations from catalog data."""

    def __init__(self, catalog: CatalogInterface | None = None) -> None:
        self._catalog = catalog or CatalogService()

    def recommend(self, sku: str) -> Recommendation:
        """Return alternative and accessory products related to `sku`.

        TODO:
            1. `product = self._catalog.get_product(sku)`.
            2. Resolve `product.alternative_sku` (and `replacement_sku`)
               into full `Product` records for `Recommendation.alternatives`.
            3. Resolve `product.accessory_skus` into full `Product`
               records for `Recommendation.accessories`.
        """
        raise NotImplementedError(
            "Brain 3 RecommendationService.recommend is not implemented yet."
        )
