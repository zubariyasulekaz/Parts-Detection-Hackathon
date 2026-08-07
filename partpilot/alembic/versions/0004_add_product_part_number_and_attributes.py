"""add manufacturer part number and visual attributes

Two additions, both aimed at telling apart products that look identical to
Brain 2.

`manufacturer_part_number` already exists for every row in catalog.csv but had
no column to land in, so `import_catalog_to_db.py` dropped it. It is the most
decisive thing a user can tell us — the number stamped on the part in their
hand — and it makes SKUs findable by the number printed on the old box.

`attributes` holds the visual facts that separate look-alike SKUs: whether a
filter is spin-on or cartridge, a pad front or rear, a pump's body colour.
These are derived from the product name and description, which were written to
describe appearance, and are exactly what a user can answer by looking at the
part rather than by knowing their car. JSONB rather than a column each because
the useful keys differ per category and will keep changing.

Revision ID: 0004
Revises: 0003
Create Date: 2026-08-06 00:00:00
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0004"
down_revision: str | None = "0003"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("products", sa.Column("manufacturer_part_number", sa.Text(), nullable=True))
    op.add_column(
        "products",
        sa.Column(
            "attributes",
            postgresql.JSONB(),
            nullable=False,
            server_default="{}",
        ),
    )
    # Lookup by the number on the part is a point query on a low-cardinality
    # text column; without this it is a sequential scan of the whole catalog.
    op.create_index(
        "ix_products_manufacturer_part_number",
        "products",
        ["manufacturer_part_number"],
    )


def downgrade() -> None:
    op.drop_index("ix_products_manufacturer_part_number", table_name="products")
    op.drop_column("products", "attributes")
    op.drop_column("products", "manufacturer_part_number")
