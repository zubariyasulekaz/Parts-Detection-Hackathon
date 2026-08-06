"""Prediction history endpoints (the audit trail).

Backed by `PredictionAuditService` — see `backend.pipeline.audit` for the
persistence layer this router exposes. Read-only by design: rows are
written by the `/predict` handler as a by-product of answering, never
posted by a client, and nothing updates or deletes them.
"""

from fastapi import APIRouter, Depends, Query

from backend.api.dependencies import get_prediction_audit_service
from backend.pipeline.audit.service import PredictionAuditService
from backend.schemas.audit import AuditEntryResponse
from backend.schemas.response import StandardResponse

router = APIRouter(prefix="/history", tags=["History"])


@router.get("", response_model=StandardResponse[list[AuditEntryResponse]])
async def list_history(
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    service: PredictionAuditService = Depends(get_prediction_audit_service),
) -> StandardResponse[list[AuditEntryResponse]]:
    """List recorded predictions, newest first.

    Every entry carries its own thumbnail as an inline data URL, so the
    payload grows by roughly 10-20 KB per row — worth keeping `limit`
    close to its default rather than paging in 200 at a time.
    """
    entries = await service.list_entries(limit=limit, offset=offset)
    return StandardResponse(data=entries)
