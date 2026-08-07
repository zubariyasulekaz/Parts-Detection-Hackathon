"""add user confirmation to the prediction audit trail

Until now the audit trail recorded only what the pipeline answered — the raw
Brain 2 top-1. Whatever the user did next (picked rank 2, answered guided
questions that eliminated the top match, walked away) was invisible, so the
trail could not say whether a prediction was actually right.

`confirmed_sku` is the SKU the user ended on, `disambiguation` the guided
question-and-answer trail that led there, `confirmed_at` when it happened.
Together they turn each corrected or confirmed run into a labeled example:
rows where `confirmed_sku` differs from `top_sku` are exactly the mistakes
worth retraining on.

Rows remain otherwise append-only; confirmation is the one amendment a row
can receive, and only once it exists.

Revision ID: 0005
Revises: 0004
Create Date: 2026-08-07 00:00:00
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0005"
down_revision: str | None = "0004"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    # No FK to products, for the same reason top_sku has none: the record
    # must stay readable after a SKU is renamed or dropped.
    op.add_column("prediction_audit", sa.Column("confirmed_sku", sa.Text(), nullable=True))
    op.add_column(
        "prediction_audit",
        sa.Column("confirmed_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "prediction_audit",
        sa.Column("disambiguation", postgresql.JSONB(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("prediction_audit", "disambiguation")
    op.drop_column("prediction_audit", "confirmed_at")
    op.drop_column("prediction_audit", "confirmed_sku")
