"""Administrative endpoints (model/index management).

Endpoint logic is intentionally NOT implemented — see per-endpoint TODOs.
All routes are gated behind `verify_api_key`.
"""

from fastapi import APIRouter, Depends

from backend.api.dependencies import get_product_service
from backend.core.security import verify_api_key
from backend.pipeline.brain3_catalog.product_service import ProductService
from backend.schemas.response import StandardResponse

router = APIRouter(
    prefix="/admin",
    tags=["Admin"],
    dependencies=[Depends(verify_api_key)],
)


@router.post("/reload-model", response_model=StandardResponse[dict])
async def reload_classifier_model() -> StandardResponse[dict]:
    """Hot-reload the Brain 1 classifier weights from `Settings.MODEL_PATH`.

    TODO: Implement by calling `ModelLoader.load()` on the shared
    `Classifier` singleton and swapping it in atomically.
    """
    return StandardResponse(message="Dummy response: model reload is not yet implemented", data={})


@router.post("/rebuild-index", response_model=StandardResponse[dict])
async def rebuild_faiss_index(category: str | None = None) -> StandardResponse[dict]:
    """Rebuild the FAISS index for one category (or all categories).

    TODO: Implement by re-embedding the catalog for `category` (or all
    categories) via Brain 2 and writing a new `FaissIndex`.

    Args:
        category: Optional single category to rebuild; rebuilds all
            categories when omitted.
    """
    return StandardResponse(
        message="Dummy response: index rebuild is not yet implemented", data={"category": category}
    )


@router.get("/catalog-stats", response_model=StandardResponse[dict])
async def catalog_stats(
    service: ProductService = Depends(get_product_service),
) -> StandardResponse[dict]:
    """Report basic product catalog statistics.

    Unlike the old flat-file design, the catalog is now PostgreSQL-backed
    and always live — there is no in-memory cache to reload, so this
    replaces the previous `reload-catalog` placeholder with a real
    (if minimal) admin action.
    """
    total = await service.count()
    return StandardResponse(data={"total_products": total})
