"""add product embeddings

Stores each product's image embedding alongside its catalog row so vector
search can run in the database instead of from FAISS files on disk.

Two columns rather than one because Brain 2 uses a different model per
category and they do not produce the same vector length: DINOv2 gives 768
dimensions, OpenCLIP 512. A pgvector column is fixed-width, so a single
column cannot hold both. `embedding_backend` records which one a row used,
so a query is always compared against vectors from the same model.

Revision ID: 0002
Revises: 0001
Create Date: 2026-08-06 00:00:00
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0002"
down_revision: str | None = "0001"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    # Supabase ships pgvector; this just enables it for this database.
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    op.add_column("products", sa.Column("embedding_768", sa.dialects.postgresql.ARRAY(sa.Float), nullable=True))
    op.add_column("products", sa.Column("embedding_512", sa.dialects.postgresql.ARRAY(sa.Float), nullable=True))
    op.add_column("products", sa.Column("embedding_backend", sa.Text(), nullable=True))

    # Swap the array columns for real vector columns. Done as raw SQL because
    # the vector type is not in SQLAlchemy's dialect without the pgvector
    # package installed at migration time.
    op.execute("ALTER TABLE products DROP COLUMN embedding_768")
    op.execute("ALTER TABLE products DROP COLUMN embedding_512")
    op.execute("ALTER TABLE products ADD COLUMN embedding_768 vector(768)")
    op.execute("ALTER TABLE products ADD COLUMN embedding_512 vector(512)")

    # No ANN index. At 55 products an exact scan is instant and exact, which
    # matches what FAISS IndexFlatIP does today; an approximate index would
    # only start paying off in the thousands.
    op.create_index("ix_products_embedding_backend", "products", ["embedding_backend"])


def downgrade() -> None:
    op.drop_index("ix_products_embedding_backend", table_name="products")
    op.drop_column("products", "embedding_backend")
    op.execute("ALTER TABLE products DROP COLUMN IF EXISTS embedding_512")
    op.execute("ALTER TABLE products DROP COLUMN IF EXISTS embedding_768")
    # The extension is left enabled - other tables may be using it.
