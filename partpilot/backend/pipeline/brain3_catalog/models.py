"""SQLAlchemy ORM model for the product catalog (Brain 3 persistence).

This is the single source of truth for the `products` table shape. The
Alembic migration in `alembic/versions/` mirrors this definition; keep
both in sync when the schema changes (and add a new migration).
"""

from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, Index, Text
from sqlalchemy.dialects.postgresql import ARRAY, JSONB
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from backend.core.database import Base


class Product(Base):
    """A single catalog product record, keyed by SKU.

    Maps 1:1 onto the `products` table. Read/write access to this model
    is only ever performed through `ProductRepository` — no other layer
    should import or query this class directly.
    """

    __tablename__ = "products"
    __table_args__ = (
        Index("ix_products_brand", "brand"),
        Index("ix_products_category", "category"),
        Index("ix_products_manufacturer_part_number", "manufacturer_part_number"),
    )

    sku: Mapped[str] = mapped_column(Text, primary_key=True)
    product_name: Mapped[str] = mapped_column(Text, nullable=False)
    brand: Mapped[str] = mapped_column(Text, nullable=False)
    category: Mapped[str] = mapped_column(Text, nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    #: The number stamped on the part / printed on the box, e.g. "DE1439".
    manufacturer_part_number: Mapped[str | None] = mapped_column(Text, nullable=True)

    #: Visual facts that separate look-alike SKUs — filter_style, position,
    #: primary_colour, and so on. Keys vary by category, hence JSONB rather
    #: than a column each. Derived from the name/description by
    #: `scripts/extract_product_attributes.py`.
    attributes: Mapped[dict[str, Any]] = mapped_column(
        JSONB, nullable=False, default=dict, server_default="{}"
    )

    image_paths: Mapped[list[str]] = mapped_column(
        ARRAY(Text), nullable=False, default=list, server_default="{}"
    )
    replacement_sku: Mapped[str | None] = mapped_column(Text, nullable=True)
    alternative_skus: Mapped[list[str]] = mapped_column(
        ARRAY(Text), nullable=False, default=list, server_default="{}"
    )
    accessory_skus: Mapped[list[str]] = mapped_column(
        ARRAY(Text), nullable=False, default=list, server_default="{}"
    )
    compatible_vehicles: Mapped[list[dict[str, Any]]] = mapped_column(
        JSONB, nullable=False, default=list, server_default="[]"
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    def __repr__(self) -> str:
        return f"Product(sku={self.sku!r}, brand={self.brand!r}, category={self.category!r})"
