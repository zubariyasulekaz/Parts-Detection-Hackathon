"""Schemas for the classification + similarity-search prediction flow
(Brain 1 and Brain 2 outputs)."""

from backend.schemas.catalog import Product
from backend.schemas.common import APIModel
from backend.schemas.recommendation import Recommendation


class PredictionRequest(APIModel):
    """Request payload for a part-identification prediction.

    Note: in practice the image is typically supplied as a `multipart/form-data`
    file upload (see `backend.api.routers.prediction`) rather than as base64
    JSON. This schema documents the logical fields and is useful for
    non-HTTP invocations (e.g. batch scripts, internal calls).
    """

    image: bytes
    filename: str


class SearchResult(APIModel):
    """A single visually-similar-product match returned by Brain 2."""

    sku: str
    similarity_score: float


class PredictionResponse(APIModel):
    """Result of the Brain 1 + Brain 2 stages: category + top-K SKU matches."""

    predicted_category: str
    confidence: float
    search_time_ms: float
    results: list[SearchResult] = []
    # True when even the closest catalog entry scored below the no-match
    # threshold: the ranked results are context, not an answer, and no
    # product was resolved. Decided server-side so every consumer (UI,
    # audit trail, API clients) gets the same verdict.
    no_match: bool = False
    # The threshold the verdict was made against, so clients can show
    # "closest 0.41 vs threshold 0.62" instead of a bare refusal.
    no_match_threshold: float | None = None
    # Embedding model that actually produced the scores (per-category, and
    # recorded on the index — may differ from the configured default).
    embedding_backend: str | None = None
    # Categories whose indexes were searched. More than one entry means the
    # classifier was uncertain and the runner-up category was searched too.
    searched_categories: list[str] = []


class PredictionResult(APIModel):
    """Full end-to-end pipeline result (Brain 1-4), as returned by `/predict`."""

    prediction: PredictionResponse
    product: Product | None = None
    recommendation: Recommendation | None = None
    explanation: str | None = None
    # Audit-trail row id for this run, when recording succeeded. Clients
    # POST the user's confirmed SKU back to /predict/{audit_id}/confirm.
    audit_id: int | None = None
