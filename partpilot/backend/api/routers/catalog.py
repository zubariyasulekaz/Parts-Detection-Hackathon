"""Catalog lookup and recommendation endpoints.

Endpoint logic is intentionally NOT implemented — see per-endpoint TODOs.
Returns dummy `Product` / `Recommendation` payloads so the API contract
is testable end-to-end before Brain 3 exists.
"""

from fastapi import APIRouter, Depends

from backend.api.dependencies import get_catalog_service, get_recommendation_service
from backend.pipeline.brain3_catalog.interfaces import (
    CatalogInterface,
    RecommendationInterface,
)
from backend.schemas.catalog import Product
from backend.schemas.recommendation import Recommendation
from backend.schemas.response import StandardResponse

router = APIRouter(prefix="/catalog", tags=["Catalog"])


@router.get("/{sku}", response_model=StandardResponse[Product])
async def get_product(
    sku: str,
    catalog: CatalogInterface = Depends(get_catalog_service),
) -> StandardResponse[Product]:
    """Fetch catalog metadata for a single SKU.

    TODO: Replace the dummy response below with `catalog.get_product(sku)`
    once Brain 3 is implemented.
    """
    dummy_product = Product(
        sku=sku,
        product_name="Placeholder Product",
        brand="Placeholder Brand",
        category="oil_filter",
        description="Placeholder description pending Brain 3 implementation.",
        compatible_vehicles=[],
        replacement_sku=None,
        alternative_sku=None,
        accessory_skus=[],
    )
    return StandardResponse(message="Dummy product (Brain 3 not yet implemented)", data=dummy_product)


@router.get("/{sku}/recommendations", response_model=StandardResponse[Recommendation])
async def get_recommendations(
    sku: str,
    recommendation_service: RecommendationInterface = Depends(get_recommendation_service),
) -> StandardResponse[Recommendation]:
    """Fetch alternative/accessory recommendations for a SKU.

    TODO: Replace the dummy response below with
    `recommendation_service.recommend(sku)` once Brain 3 is implemented.
    """
    dummy_recommendation = Recommendation(alternatives=[], accessories=[])
    return StandardResponse(
        message="Dummy recommendation (Brain 3 not yet implemented)", data=dummy_recommendation
    )
