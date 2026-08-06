"""SQLAlchemy ORM model for the prediction audit trail.

This is the single source of truth for the `prediction_audit` table
shape. The Alembic migration in `alembic/versions/` mirrors this
definition; keep both in sync when the schema changes (and add a new
migration).
"""

from datetime import datetime
from typing import Any

from sqlalchemy import BigInteger, DateTime, Float, Index, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from backend.core.database import Base


class PredictionAudit(Base):
    """One recorded `/predict` run, keyed by a surrogate id.

    Maps 1:1 onto the `prediction_audit` table. Rows are append-only,
    with one exception: the user's confirmation (`confirmed_sku`,
    `confirmed_at`, `disambiguation`) may be written once after the fact,
    turning the row from "what the pipeline said" into "what the pipeline
    said and whether it was right". Read/write access to this model is
    only ever performed through `PredictionAuditRepository` — no other
    layer should import or query this class directly.

    `top_sku` and `confirmed_sku` deliberately carry no foreign key to
    `products`: they record what was answered at the time, and that
    answer must stay readable after a SKU is renamed or dropped from the
    catalog.
    """

    __tablename__ = "prediction_audit"
    __table_args__ = (Index("ix_prediction_audit_created_at", "created_at"),)

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    predicted_category: Mapped[str] = mapped_column(Text, nullable=False)
    confidence: Mapped[float] = mapped_column(Float, nullable=False)
    search_time_ms: Mapped[float] = mapped_column(Float, nullable=False)

    top_sku: Mapped[str | None] = mapped_column(Text, nullable=True)
    candidates: Mapped[list[dict[str, Any]]] = mapped_column(
        JSONB, nullable=False, default=list, server_default="[]"
    )
    embedding_backend: Mapped[str | None] = mapped_column(Text, nullable=True)
    explanation: Mapped[str | None] = mapped_column(Text, nullable=True)
    # A downscaled JPEG as a base64 data URL. Uploads are not stored
    # anywhere, so this is the only surviving trace of the image.
    thumbnail: Mapped[str | None] = mapped_column(Text, nullable=True)

    # The SKU the user settled on (via Confirm Match or the guided
    # questions), when they told us. Differing from `top_sku` marks the
    # run as a correction — a labeled example the pipeline got wrong.
    confirmed_sku: Mapped[str | None] = mapped_column(Text, nullable=True)
    confirmed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    # The guided disambiguation Q&A trail that led to the confirmation,
    # e.g. {"attr:position": "front", "make": "Honda"}.
    disambiguation: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)

    def __repr__(self) -> str:
        return (
            f"PredictionAudit(id={self.id!r}, "
            f"predicted_category={self.predicted_category!r}, top_sku={self.top_sku!r})"
        )
