"""Prediction history endpoints (the audit trail).

Backed by `PredictionAuditService` — see `backend.pipeline.audit` for the
persistence layer this router exposes. Rows are written by the `/predict`
handler as a by-product of answering and are never posted by a client, so
there is no create or update endpoint; the one write a client can make is
deleting a row it no longer wants listed.
"""

from fastapi import APIRouter, Depends, Path, Query

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


@router.delete("/{entry_id}", response_model=StandardResponse[dict])
async def delete_history_entry(
    entry_id: int = Path(ge=1, description="Audit row id, as returned by `GET /history`."),
    service: PredictionAuditService = Depends(get_prediction_audit_service),
) -> StandardResponse[dict]:
    """Delete one recorded prediction.

    Args:
        entry_id: Primary key of the row to remove. Not a SKU — one SKU
            can be the top match of many runs.

    Raises:
        backend.core.exceptions.AuditEntryNotFound: If `entry_id` is
            unknown, mapped to a 404 by the global handler.
    """
    await service.delete_entry(entry_id)
    return StandardResponse(message="History entry deleted", data={"id": entry_id})
