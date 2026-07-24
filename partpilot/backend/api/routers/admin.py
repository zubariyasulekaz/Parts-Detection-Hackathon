"""Administrative endpoints (model/index management).

Endpoint logic is intentionally NOT implemented — see per-endpoint TODOs.
All routes are gated behind `verify_api_key`.
"""

from fastapi import APIRouter, Depends

from backend.core.security import verify_api_key
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


@router.post("/reload-catalog", response_model=StandardResponse[dict])
async def reload_catalog() -> StandardResponse[dict]:
    """Reload catalog metadata from `Settings.CATALOG_PATH`.

    TODO: Implement by calling `MetadataLoader.load()` on the shared
    `CatalogService` singleton.
    """
    return StandardResponse(message="Dummy response: catalog reload is not yet implemented", data={})
