"""Schemas for the classification + similarity-search prediction flow
(Brain 1 and Brain 2 outputs)."""

from backend.schemas.common import APIModel


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
    """Result of the end-to-end prediction pipeline."""

    predicted_category: str
    confidence: float
    search_time_ms: float
    results: list[SearchResult] = []
