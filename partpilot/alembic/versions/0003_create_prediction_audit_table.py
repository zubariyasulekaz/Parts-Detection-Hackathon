"""create prediction audit table

Keeps a record of what the pipeline answered for each `/predict` call.
Until now a prediction existed only in the HTTP response and was gone
the moment it was returned.

`candidates` is a JSONB document rather than a child table: the ranked
matches are written once, always read whole, and never joined or
searched by SKU, so a document column keeps a recording to one INSERT.
For the same reason `top_sku` carries no foreign key to `products` — the
trail records the answer that was given, and must stay readable after a
SKU is renamed or removed from the catalog.

`thumbnail` holds a downscaled JPEG as a base64 data URL, roughly
10-20 KB per row. Uploads are not written to disk or object storage
anywhere in the app, so inlining the image is what makes an audit row
self-contained.

Revision ID: 0003
Revises: 0002
Create Date: 2026-08-06 00:00:00
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

revision: str = "0003"
down_revision: str | None = "0002"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "prediction_audit",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("predicted_category", sa.Text(), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=False),
        sa.Column("search_time_ms", sa.Float(), nullable=False),
        sa.Column("top_sku", sa.Text(), nullable=True),
        sa.Column(
            "candidates",
            JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default="[]",
        ),
        sa.Column("embedding_backend", sa.Text(), nullable=True),
        sa.Column("explanation", sa.Text(), nullable=True),
        sa.Column("thumbnail", sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint("id", name="pk_prediction_audit"),
    )
    # The history page only ever reads newest-first; this is the index
    # that keeps that ordering off a full table scan as rows accumulate.
    op.create_index("ix_prediction_audit_created_at", "prediction_audit", ["created_at"])


def downgrade() -> None:
    op.drop_index("ix_prediction_audit_created_at", table_name="prediction_audit")
    op.drop_table("prediction_audit")
