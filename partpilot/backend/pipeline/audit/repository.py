"""Prediction audit repository.

The ONLY module in the audit package allowed to talk to the database.
Every method here is a thin, typed wrapper around a SQLAlchemy statement
— no business rules (best-effort degradation, error translation, logging
of domain events) belong in this class. See `PredictionAuditService` for
that.
"""

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.logging import get_logger
from backend.pipeline.audit.models import PredictionAudit as PredictionAuditORM
from backend.schemas.audit import AuditEntryCreate

logger = get_logger(__name__)


class PredictionAuditRepository:
    """Async append/read access to the `prediction_audit` table.

    Args:
        session: Request-scoped `AsyncSession`, injected via
            `backend.api.dependencies.get_prediction_audit_repository`.
    """

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(self, data: AuditEntryCreate) -> PredictionAuditORM:
        """Insert a new audit row.

        Args:
            data: Validated record of a finished prediction.

        Returns:
            The persisted ORM instance, refreshed so DB-generated fields
            (`id`, `created_at`) are populated.
        """
        # `mode="json"` so nested models reach JSONB as plain JSON types,
        # which is all asyncpg can encode.
        entry = PredictionAuditORM(**data.model_dump(mode="json"))
        self._session.add(entry)
        await self._session.flush()
        await self._session.refresh(entry)
        return entry

    async def get_all(self, limit: int = 50, offset: int = 0) -> list[PredictionAuditORM]:
        """List audit rows newest-first, with pagination.

        `id` breaks ties on `created_at` so paging stays stable when two
        predictions land in the same clock tick.
        """
        stmt = (
            select(PredictionAuditORM)
            .order_by(PredictionAuditORM.created_at.desc(), PredictionAuditORM.id.desc())
            .limit(limit)
            .offset(offset)
        )
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def delete(self, entry_id: int) -> bool:
        """Delete one audit row by primary key.

        Returns:
            `True` if a row was deleted, `False` if `entry_id` did not exist.
        """
        entry = await self._session.get(PredictionAuditORM, entry_id)
        if entry is None:
            return False
        await self._session.delete(entry)
        await self._session.flush()
        return True

    async def count(self) -> int:
        """Return the total number of recorded predictions."""
        stmt = select(func.count()).select_from(PredictionAuditORM)
        result = await self._session.execute(stmt)
        return result.scalar_one()

    async def commit(self) -> None:
        """Persist the audit row now, rather than leaving it to `get_db`.

        `get_db` commits once the handler returns, which is *after*
        `/predict` has already built its 200 but before FastAPI sends it —
        so a commit that fails there (dropped pooler connection, statement
        timeout) would turn a good prediction into a 500. Committing here
        keeps every way the write can fail inside the guarded block in
        `PredictionAuditService.record`, and leaves `get_db` nothing to do.
        Only that method should call this.
        """
        await self._session.commit()

    async def rollback(self) -> None:
        """Discard the session's pending work after a failed write.

        `/predict` shares one `AsyncSession` with Brain 3, and a failed
        INSERT leaves it in a failed-transaction state that `get_db`
        would only discover on its end-of-request commit. Only
        `PredictionAuditService.record` should call this.
        """
        await self._session.rollback()
