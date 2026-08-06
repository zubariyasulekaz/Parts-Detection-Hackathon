"""Schemas describing recorded predictions (the audit trail).

`AuditEntryCreate` is the write-side payload the `/predict` handler
builds once a run finishes; `AuditEntryResponse` is what gets serialized
back out, including DB-generated fields (`id`, `created_at`). Both build
on `AuditEntryBase` so field definitions live in exactly one place.

Neither is a request body — audit rows are written by the pipeline, never
posted by a client.
"""

from datetime import datetime

from pydantic import ConfigDict, Field

from backend.schemas.common import APIModel


class AuditCandidate(APIModel):
    """One Brain 2 match, as recorded in the audit trail.

    Mirrors `backend.schemas.prediction.SearchResult` plus the position
    the match held in the result list. `rank` is stored rather than
    derived because the JSONB column is read back as an opaque document
    and its element order is not something to depend on.
    """

    sku: str = Field(min_length=1)
    similarity_score: float
    rank: int = Field(ge=1)


class AuditEntryBase(APIModel):
    """Fields shared by every audit create/response payload."""

    predicted_category: str = Field(min_length=1)
    confidence: float
    search_time_ms: float
    top_sku: str | None = None
    candidates: list[AuditCandidate] = Field(default_factory=list)
    embedding_backend: str | None = None
    explanation: str | None = None
    thumbnail: str | None = None


class AuditEntryCreate(AuditEntryBase):
    """Payload passed to `PredictionAuditService.record`."""


class AuditEntryResponse(AuditEntryBase):
    """A recorded prediction, as returned by the history API.

    `from_attributes=True` lets this be built directly from a
    `backend.pipeline.audit.models.PredictionAudit` ORM instance via
    `AuditEntryResponse.model_validate(orm_instance)`.
    """

    model_config = ConfigDict(from_attributes=True)

    id: int
    created_at: datetime
