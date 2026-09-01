"""Part identification for the RigidHitch catalogue.

The whole of the application's search surface. Three things it deliberately
does not do, each because the data does not support it:

* **No category classifier.** 50.9% of products sit in more than one top-level
  category, so there is no single correct route for a query. Every search goes
  against one flat index instead, and the category reported is read off the top
  match rather than predicted.
* **No recommendations.** The source data has no replacement, alternative or
  accessory links at all, so the response omits them rather than returning
  empty lists that read like "none apply".
* **No similarity threshold.** Measured on this catalogue, a cosine cutoff is
  close to useless: rejecting 9% of correct matches catches only 57% of wrong
  ones. Ambiguity is reported through the top-2 margin instead, which does
  carry signal.
"""

import time
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, File, Query, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from backend.api.dependencies import get_app_settings, get_rigidhitch_search
from backend.config.settings import Settings
from backend.core.database import get_rigidhitch_db
from backend.core.exceptions import InvalidImage, ProductNotFound
from backend.core.logging import get_logger
from backend.pipeline.brain2_similarity.search import SimilaritySearchService
from backend.pipeline.brain3_catalog.rigidhitch_catalog import RigidHitchCatalog
from backend.schemas.response import StandardResponse
from backend.utils.image_utils import load_image_from_bytes, remove_background

logger = get_logger(__name__)

router = APIRouter(prefix="/rigidhitch", tags=["RigidHitch"])

# Below this gap between the best and second-best product, the search is not
# really choosing - it is split between near-identical parts, most often the
# same item in a different size, which a photograph cannot show. Measured: in
# the narrowest 30% of margins top-1 is right 19.2% of the time, against 47.4%
# above it. The UI should offer the shortlist here rather than assert an answer.
AMBIGUOUS_MARGIN = 0.036

# Refuse outright below this score. Deliberately far under the catalogue's own
# 1st percentile (0.190) and the ~0.34 seen on real phone photographs of parts
# we do stock, because of what the measurements say this cutoff can and cannot
# do (scripts/rigidhitch_measure_refusal.py):
#
# * It catches input that is not a trailer part at all - a hand, a pet, a wall.
# * It does NOT catch a part we simply do not stock. Nothing does. On a sample
#   of 200, similarity, top-2 margin and SIFT/RANSAC geometric verification all
#   failed to separate the true product from its nearest rival; verification was
#   marginally inverted (median 12 inliers for the rival against 11 for the
#   truth). An unstocked ball mount looks like a stocked one because it is the
#   same shape, so no signal computed from the photograph can tell them apart.
#
# The second case is handled by asking the brand instead - see /brands.
NOT_A_PART_SCORE = 0.15


def _as_product(product: dict) -> dict:
    """Shape a RigidHitch product like PartPilot's `ProductResponse`.

    The frontend already renders that shape, so matching it keeps the UI
    change to a URL rather than a rewrite. The four fields RigidHitch has no
    data for are returned empty rather than omitted - the contract says they
    exist, and an empty list is the honest answer to "what accessories go with
    this" when the source data has none.

    `image_paths` carries absolute URLs, not the stored relative paths: the
    frontend drops any non-http value to a placeholder without logging, so a
    relative path here is invisible rather than broken.
    """
    now = datetime.now(timezone.utc).isoformat()
    attributes = product.get("attributes") or {}
    return {
        "sku": product.get("sku", ""),
        "product_name": product.get("product_name") or product.get("sku", ""),
        "brand": product.get("brand") or "Unknown",
        "category": product.get("category") or "",
        "description": product.get("description"),
        "manufacturer_part_number": product.get("manufacturer_part_number"),
        "attributes": {k: str(v) for k, v in attributes.items()},
        "image_paths": product.get("images", []),
        # RigidHitch's source data has no cross-references at all.
        "replacement_sku": None,
        "alternative_skus": [],
        "accessory_skus": [],
        "compatible_vehicles": [],
        "created_at": now,
        "updated_at": now,
    }


@router.post("/predict", response_model=StandardResponse[dict])
async def predict_rigidhitch_part(
    file: UploadFile = File(...),
    top_k: int = Query(default=5, ge=1, le=50),
    explain: bool = Query(default=False, description="Accepted for interface parity; unused."),
    search: SimilaritySearchService = Depends(get_rigidhitch_search),
    session: AsyncSession = Depends(get_rigidhitch_db),
    settings: Settings = Depends(get_app_settings),
) -> StandardResponse[dict]:
    """Identify a RigidHitch part from a photograph.

    Returns the same envelope as `/predict` so the existing frontend renders it
    unchanged, with the parts RigidHitch genuinely lacks left empty rather than
    invented:

    * `predicted_category` is the **top match's** category, read off the result.
      It is not a prediction - there is no classifier - and confidence is the
      match score, not a class probability.
    * `recommendation` is null: the source data has no replacement, alternative
      or accessory links.
    * `explanation` carries the ambiguity note when the top two are too close
      to separate, which is the one thing a user most needs told.
    """
    content = await file.read()
    max_bytes = settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024
    if len(content) > max_bytes:
        raise InvalidImage(f"Uploaded image exceeds the {settings.MAX_UPLOAD_SIZE_MB} MB limit.")

    raw_image = load_image_from_bytes(content)
    # The index was built from background-removed photographs; a query has to be
    # treated the same way or it is being compared against a different
    # distribution. Whitening is applied inside FaissIndex, so it cannot be
    # forgotten here.
    started = time.perf_counter()
    cleaned = remove_background(raw_image)

    outcome = search.search(
        category=settings.RIGIDHITCH_CATEGORY,
        image=cleaned,
        top_k=top_k,
        raw_image=raw_image,
    )
    elapsed_ms = (time.perf_counter() - started) * 1000

    catalog = RigidHitchCatalog(session)
    details = await catalog.get_many([m.sku for m in outcome.matches])

    results = [
        {"sku": m.sku, "similarity_score": m.similarity_score} for m in outcome.matches
    ]
    top = details.get(outcome.matches[0].sku) if outcome.matches else None

    best = outcome.matches[0].similarity_score if outcome.matches else 0.0
    margin = (
        outcome.matches[0].similarity_score - outcome.matches[1].similarity_score
        if len(outcome.matches) >= 2 else 1.0
    )
    ambiguous = margin < AMBIGUOUS_MARGIN
    not_a_part = not outcome.matches or best < NOT_A_PART_SCORE

    logger.info(
        "RigidHitch: %d matches, top=%s (%.3f), margin %.4f%s%s",
        len(results),
        outcome.matches[0].sku if outcome.matches else "-",
        best,
        margin,
        " AMBIGUOUS" if ambiguous else "",
        " NOT-A-PART" if not_a_part else "",
    )

    return StandardResponse(data={
        "prediction": {
            # Read off the winning result, not predicted from the photo -
            # RigidHitch has no classifier.
            "predicted_category": (top or {}).get("category") or "",
            "confidence": best,
            "search_time_ms": elapsed_ms,
            "results": results,
            # Fires only for input that is not a trailer part at all. It cannot
            # detect a part RigidHitch does not stock - see NOT_A_PART_SCORE for
            # why no image-derived signal can. The UI must therefore always
            # offer "none of these", and confirming the brand is what actually
            # rules a stranger out.
            "no_match": not_a_part,
            "no_match_threshold": NOT_A_PART_SCORE,
            "embedding_backend": outcome.backend,
            "searched_categories": [settings.RIGIDHITCH_CATEGORY],
        },
        "product": None if not_a_part else (_as_product(top) if top else None),
        "recommendation": None,
        "explanation": (
            "This does not look like a trailer part. Try a photograph of the part alone, "
            "filling the frame, against a plain background."
            if not_a_part else
            "The top two candidates score almost the same, which usually means they are "
            "the same part in a different size - a photograph cannot show that. Compare "
            "the shortlist below, or measure the part, before choosing."
            if ambiguous else None
        ),
        "audit_id": None,
    })


@router.get("/brands", response_model=StandardResponse[list[str]])
async def list_rigidhitch_brands(
    session: AsyncSession = Depends(get_rigidhitch_db),
) -> StandardResponse[list[str]]:
    """Every brand RigidHitch stocks, for ruling a part out by name.

    This is the one refusal path that works. A photograph cannot distinguish an
    unstocked ball mount from a stocked one - they are the same shape, and all
    three measured signals failed on exactly that case. The brand is the piece
    of information the shape does not carry, and it is usually printed on the
    part or its label.

    So the UI asks the brand and offers "not listed": a customer holding a
    METOWARE mount picks that, and the honest answer follows immediately, rather
    than the search asserting the nearest Curt.
    """
    brands = await RigidHitchCatalog(session).brands()
    return StandardResponse(data=brands)


@router.get("/products", response_model=StandardResponse[list[dict]])
async def list_rigidhitch_products(
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    category: str | None = Query(default=None),
    brand: str | None = Query(default=None),
    session: AsyncSession = Depends(get_rigidhitch_db),
) -> StandardResponse[list[dict]]:
    """Browse the RigidHitch catalogue.

    Paged rather than unbounded: 10,813 products is far past what any page
    should fetch at once, and PartPilot's 56 never forced the question.
    """
    products = await RigidHitchCatalog(session).list_products(
        limit=limit, offset=offset, category=category, brand=brand
    )
    return StandardResponse(data=[_as_product(p) for p in products])


@router.get("/products/{sku}", response_model=StandardResponse[dict])
async def get_rigidhitch_product(
    sku: str,
    session: AsyncSession = Depends(get_rigidhitch_db),
) -> StandardResponse[dict]:
    """One RigidHitch product by SKU.

    Mounted at `/products/{sku}` under this router's prefix so it mirrors
    PartPilot's path, and returns the same shape - the frontend fetches a
    product's details separately after a search, and that call has to land on
    the right catalogue or every result 404s.
    """
    product = await RigidHitchCatalog(session).get_product(sku)
    if product is None:
        raise ProductNotFound(f"Product with SKU '{sku}' was not found.")
    return StandardResponse(data=_as_product(product))


@router.get("/products/{sku}/recommendations", response_model=StandardResponse[dict])
async def get_rigidhitch_recommendations(sku: str) -> StandardResponse[dict]:
    """Always empty for RigidHitch.

    Its source data carries no replacement, alternative or accessory links at
    all, so there is nothing to recommend. Answered here rather than left to
    404 against PartPilot's route, which would look like a failure rather than
    an honest "this catalogue has none".
    """
    return StandardResponse(
        message="RigidHitch's catalogue has no replacement or accessory data.",
        data={"product_sku": sku, "alternatives": [], "accessories": []},
    )
