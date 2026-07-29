"""Product catalog CRUD endpoints (Brain 3 persistence layer).

Backed by `ProductService`, which wraps `ProductRepository` for all
database access — see `backend.pipeline.brain3_catalog` for the
persistence layer this router exposes. This is the layer Brain 2 (via
the orchestrator) uses to resolve a matched SKU to full catalog
metadata once similarity search is implemented.
"""

from fastapi import APIRouter, Depends, Query, status

from backend.api.dependencies import get_product_service, get_recommendation_service
from backend.pipeline.brain3_catalog.interfaces import RecommendationInterface
from backend.pipeline.brain3_catalog.product_service import ProductService
from backend.schemas.catalog import ProductCreate, ProductResponse, ProductUpdate
from backend.schemas.recommendation import Recommendation
from backend.schemas.response import StandardResponse

router = APIRouter(prefix="/products", tags=["Products"])


@router.get("", response_model=StandardResponse[list[ProductResponse]])
async def list_products(
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    category: str | None = Query(default=None, description="Filter by exact category match."),
    brand: str | None = Query(default=None, description="Filter by exact brand match."),
    service: ProductService = Depends(get_product_service),
) -> StandardResponse[list[ProductResponse]]:
    """List catalog products, optionally filtered by category or brand.

    `category` and `brand` are mutually exclusive filters; if both are
    supplied, `category` takes precedence.
    """
    if category is not None:
        products = await service.search_by_category(category, limit=limit)
    elif brand is not None:
        products = await service.search_by_brand(brand, limit=limit)
    else:
        products = await service.list_products(limit=limit, offset=offset)
    return StandardResponse(data=products)


@router.get("/{sku}", response_model=StandardResponse[ProductResponse])
async def get_product(
    sku: str,
    service: ProductService = Depends(get_product_service),
) -> StandardResponse[ProductResponse]:
    """Fetch a single catalog product by SKU."""
    product = await service.get_product(sku)
    return StandardResponse(data=product)


@router.post(
    "",
    response_model=StandardResponse[ProductResponse],
    status_code=status.HTTP_201_CREATED,
)
async def create_product(
    payload: ProductCreate,
    service: ProductService = Depends(get_product_service),
) -> StandardResponse[ProductResponse]:
    """Create a new catalog product."""
    product = await service.create_product(payload)
    return StandardResponse(message="Product created", data=product)


@router.put("/{sku}", response_model=StandardResponse[ProductResponse])
async def update_product(
    sku: str,
    payload: ProductUpdate,
    service: ProductService = Depends(get_product_service),
) -> StandardResponse[ProductResponse]:
    """Partially update an existing catalog product."""
    product = await service.update_product(sku, payload)
    return StandardResponse(message="Product updated", data=product)


@router.delete("/{sku}", response_model=StandardResponse[dict])
async def delete_product(
    sku: str,
    service: ProductService = Depends(get_product_service),
) -> StandardResponse[dict]:
    """Delete a catalog product."""
    await service.delete_product(sku)
    return StandardResponse(message="Product deleted", data={"sku": sku})


@router.get("/{sku}/recommendations", response_model=StandardResponse[Recommendation])
async def get_recommendations(
    sku: str,
    recommendation_service: RecommendationInterface = Depends(get_recommendation_service),
) -> StandardResponse[Recommendation]:
    """Fetch alternative/accessory recommendations for a SKU.

    TODO: `RecommendationService.recommend` is not yet implemented —
    see `backend.pipeline.brain3_catalog.recommendation_service`.
    """
    recommendation = await recommendation_service.recommend(sku)
    return StandardResponse(data=recommendation)
