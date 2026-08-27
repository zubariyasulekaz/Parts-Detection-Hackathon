"""Table definition for the RigidHitch `products` table.

The single source of truth for RigidHitch's schema - imported by both this
migration environment (so `alembic upgrade head` creates exactly this table)
and `scripts/import_rigidhitch_catalog.py` (so the import script inserts into
exactly what the migration created, instead of each keeping its own copy of
the column list and drifting apart).

This is a plain SQLAlchemy Core `Table`, not an ORM model living on the main
app's `backend.core.database.Base` - RigidHitch is a separate database with a
different products schema (no replacement_sku/alternative_skus/accessory_skus/
compatible_vehicles; RigidHitch's source data has 0% coverage on all four, and
its fitment tags land in `attributes.fitment` instead - see
`scripts/import_rigidhitch_catalog.py` for why).
"""

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import ARRAY, JSONB

metadata = sa.MetaData()

products_table = sa.Table(
    "products",
    metadata,
    sa.Column("sku", sa.Text(), primary_key=True),
    sa.Column("product_name", sa.Text(), nullable=False),
    sa.Column("brand", sa.Text(), nullable=False),
    sa.Column("category", sa.Text(), nullable=False),
    sa.Column("description", sa.Text(), nullable=True),
    sa.Column("manufacturer_part_number", sa.Text(), nullable=True),
    sa.Column("attributes", JSONB, nullable=False, server_default="{}"),
    sa.Column("image_paths", ARRAY(sa.Text()), nullable=False, server_default="{}"),
    sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    sa.Column(
        "updated_at",
        sa.DateTime(timezone=True),
        server_default=sa.text("now()"),
        onupdate=sa.text("now()"),
        nullable=False,
    ),
    sa.Index("ix_products_brand", "brand"),
    sa.Index("ix_products_category", "category"),
    sa.Index("ix_products_manufacturer_part_number", "manufacturer_part_number"),
)
