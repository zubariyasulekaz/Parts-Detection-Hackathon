"""Prediction Audit Service.

The ONLY module audit-trail consumers (the `/predict` handler that
writes and the history API that reads) should call. Wraps
`PredictionAuditRepository`, translating ORM instances to the public
Pydantic schemas, and owns the policy that recording a prediction must
never cost the caller that prediction. Contains no direct database
access — see `PredictionAuditRepository` for that.
"""

from backend.core.exceptions import AuditEntryNotFound
from backend.core.logging import get_logger
from backend.pipeline.audit.repository import PredictionAuditRepository
from backend.schemas.audit import AuditEntryCreate, AuditEntryResponse

logger = get_logger(__name__)


class PredictionAuditService:
    """Business-facing prediction audit trail service.

    Args:
        repository: Async repository providing raw DB access. Injected
            per-request via
            `backend.api.dependencies.get_prediction_audit_service`.
    """

    def __init__(self, repository: PredictionAuditRepository) -> None:
        self._repository = repository

    async def record(self, entry: AuditEntryCreate) -> AuditEntryResponse | None:
        """Record one finished prediction.

        The audit trail is a by-product of answering, never a
        precondition for it, so a write failure (most likely migration
        `0003` not yet applied) degrades exactly like a Brain 4 outage
        in `PipelineOrchestrator.run`: log it and let the caller keep
        its result. Committing and rolling back here is what makes that
        safe: the session is shared with Brain 3, so anything left
        pending — a failed INSERT, or a successful one still awaiting
        commit — would resurface out of `get_db` after the handler has
        already produced its response, where nothing can catch it.

        Returns:
            The recorded entry, or `None` if it could not be written.
        """
        try:
            entry_orm = await self._repository.create(entry)
            await self._repository.commit()
        except Exception as exc:  # noqa: BLE001
            await self._repository.rollback()
            logger.warning("Prediction not recorded; returning the result anyway: %s", exc)
            return None

        logger.info("Prediction recorded: id=%s top_sku=%s", entry_orm.id, entry_orm.top_sku)
        return AuditEntryResponse.model_validate(entry_orm)

    async def confirm(
        self,
        entry_id: int,
        confirmed_sku: str,
        disambiguation: dict | None = None,
    ) -> AuditEntryResponse:
        """Record which SKU the user settled on for a recorded run.

        This is the feedback loop the audit trail exists for: rows where
        the confirmation differs from `top_sku` are labeled examples of
        the pipeline being wrong. Unlike `record`, the user asked for this
        write, so failures propagate instead of being swallowed.

        Raises:
            backend.core.exceptions.AuditEntryNotFound: If `entry_id` is
                unknown.
        """
        entry_orm = await self._repository.set_confirmation(
            entry_id, confirmed_sku, disambiguation
        )
        if entry_orm is None:
            raise AuditEntryNotFound(f"Prediction history entry {entry_id} was not found.")
        logger.info(
            "Prediction %s confirmed as %s%s",
            entry_id,
            confirmed_sku,
            " (correction)" if entry_orm.top_sku != confirmed_sku else "",
        )
        return AuditEntryResponse.model_validate(entry_orm)

    async def list_entries(self, limit: int = 50, offset: int = 0) -> list[AuditEntryResponse]:
        """List recorded predictions, newest first, with pagination."""
        entries = await self._repository.get_all(limit=limit, offset=offset)
        return [AuditEntryResponse.model_validate(e) for e in entries]

    async def delete_entry(self, entry_id: int) -> None:
        """Delete one recorded prediction.

        Unlike `record`, a failure here must not be swallowed: the caller
        asked for the deletion and has to know whether it happened.

        Raises:
            backend.core.exceptions.AuditEntryNotFound: If `entry_id` is
                unknown (already deleted, or never existed).
        """
        if not await self._repository.delete(entry_id):
            raise AuditEntryNotFound(f"Prediction history entry {entry_id} was not found.")
        logger.info("Prediction history entry deleted: id=%s", entry_id)

    async def count(self) -> int:
        """Return the total number of recorded predictions."""
        return await self._repository.count()
