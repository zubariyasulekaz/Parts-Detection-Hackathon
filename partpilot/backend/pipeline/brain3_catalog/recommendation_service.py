"""Concrete `RecommendationInterface` implementation.

Produces alternative and accessory product recommendations for a given
SKU, based on catalog metadata (`replacement_sku`, `alternative_skus`,
`accessory_skus` fields).
"""

from backend.core.logging import get_logger
from backend.pipeline.brain3_catalog.interfaces import (
    CatalogInterface,
    RecommendationInterface,
)
from backend.schemas.recommendation import Recommendation

logger = get_logger(__name__)


class RecommendationService(RecommendationInterface):
    """Builds alternative/accessory recommendations from catalog data.

    Args:
        catalog: Catalog reader used to resolve SKUs to full product
            records. Injected via `backend.api.dependencies.get_recommendation_service`
            (typically a `ProductService` instance).
    """

    def __init__(self, catalog: CatalogInterface) -> None:
        self._catalog = catalog

    async def recommend(self, sku: str) -> Recommendation:
        """Return alternative and accessory products related to `sku`.

        TODO:
            1. `product = await self._catalog.get_product(sku)`.
            2. Resolve `product.replacement_sku` and each entry in
               `product.alternative_skus` into full product records for
               `Recommendation.alternatives` (skipping any that no
               longer exist).
            3. Resolve each entry in `product.accessory_skus` into full
               product records for `Recommendation.accessories`.
        """
        raise NotImplementedError(
            "Brain 3 RecommendationService.recommend is not implemented yet."
        )
