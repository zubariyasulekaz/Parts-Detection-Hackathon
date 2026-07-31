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


class PredictionResult(APIModel):
    """Full end-to-end pipeline result (Brain 1-4), as returned by `/predict`."""

    prediction: PredictionResponse
    product: Product | None = None
    recommendation: Recommendation | None = None
    explanation: str | None = None
