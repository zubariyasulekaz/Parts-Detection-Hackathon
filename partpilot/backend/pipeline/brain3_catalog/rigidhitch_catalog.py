"""Product lookup for the RigidHitch catalogue.

Separate from `product_service.py` because the two catalogues genuinely differ.
PartPilot's `Product` ORM declares `replacement_sku`, `alternative_skus`,
`accessory_skus` and `compatible_vehicles`; RigidHitch's table has none of them,
because its source data is 0% populated for all four (see
`scripts/import_rigidhitch_catalog.py`). Querying one table with the other's
model raises `UndefinedColumn`, so this defines only the columns that exist.

The absence of those columns has a product consequence worth stating: there are
no accessory or replacement recommendations for RigidHitch, and the API returns
none rather than an empty list dressed up as an answer.
"""

from typing import Any

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import ARRAY, JSONB
from sqlalchemy.ext.asyncio import AsyncSession

from backend.config.settings import get_settings
from backend.core.logging import get_logger

logger = get_logger(__name__)

# Core Table rather than an ORM class on the shared `Base`: registering a
# second `products` mapping on the same metadata would collide with
# PartPilot's. This mirrors alembic_rigidhitch/schema.py, which owns the DDL.
_metadata = sa.MetaData()
products = sa.Table(
    "products",
    _metadata,
    sa.Column("sku", sa.Text(), primary_key=True),
    sa.Column("product_name", sa.Text()),
    sa.Column("brand", sa.Text()),
    sa.Column("category", sa.Text()),
    sa.Column("description", sa.Text()),
    sa.Column("manufacturer_part_number", sa.Text()),
    sa.Column("attributes", JSONB),
    sa.Column("image_paths", ARRAY(sa.Text())),
)


def _image_urls(paths: list[str] | None) -> list[str]:
    """Turn stored relative paths into URLs a browser can actually load.

    The catalogue stores `images/<sku>/<file>.jpg`, which resolves to nothing
    in a browser - and the frontend drops any non-http URL to a placeholder
    silently, so this is the difference between a working demo and a page of
    grey boxes with no error to explain them.
    """
    base = get_settings().RIGIDHITCH_IMAGE_BASE_URL.rstrip("/")
    return [f"{base}/{path.lstrip('/')}" for path in (paths or [])]


class RigidHitchCatalog:
    """Reads RigidHitch products by SKU."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_product(self, sku: str) -> dict[str, Any] | None:
        """One product as a plain dict, with image paths resolved to URLs."""
        row = (await self._session.execute(
            sa.select(products).where(products.c.sku == sku)
        )).mappings().first()
        return self._to_dict(row) if row else None

    async def get_many(self, skus: list[str]) -> dict[str, dict[str, Any]]:
        """Several products at once, keyed by SKU.

        A search returns five candidates; fetching them individually would be
        five round trips per request.
        """
        if not skus:
            return {}
        rows = (await self._session.execute(
            sa.select(products).where(products.c.sku.in_(skus))
        )).mappings().all()
        return {row["sku"]: self._to_dict(row) for row in rows}

    async def find_by_part_number(self, tokens: list[str]) -> str | None:
        """The SKU named by the best of `tokens`, in the order the caller gave them.

        Both sides are stripped to letters and digits before comparison,
        because a part number is punctuated one way in the database, another on
        the printed label, and a third by whatever OCR makes of the label.

        Matches the manufacturer's part number as well as the SKU: a label more
        often carries the maker's number than the number RigidHitch files it
        under.

        The caller's order is the ranking, and it carries the judgement - see
        `part_number_ocr.read_candidate_tokens`, which puts a label's own
        numbers ahead of the ones it says it replaces. This walks that order
        and takes the first token naming exactly one product. A token naming
        several is skipped rather than guessed at.

        Returns None when nothing matches, which is the overwhelmingly common
        case: measured at 2% of real photographs.
        """
        if not tokens:
            return None
        stripped_sku = sa.func.regexp_replace(
            sa.func.upper(products.c.sku), "[^A-Z0-9]", "", "g"
        )
        stripped_mpn = sa.func.regexp_replace(
            sa.func.upper(sa.func.coalesce(products.c.manufacturer_part_number, "")),
            "[^A-Z0-9]", "", "g",
        )
        # One round trip for every token, carrying back which token matched so
        # the caller's ordering can be applied here rather than in SQL.
        rows = (await self._session.execute(
            sa.select(
                products.c.sku,
                sa.case(
                    (stripped_sku.in_(tokens), stripped_sku), else_=stripped_mpn
                ).label("token"),
            ).where(sa.or_(stripped_sku.in_(tokens), stripped_mpn.in_(tokens)))
            .limit(50)
        )).mappings().all()
        if not rows:
            return None

        by_token: dict[str, set[str]] = {}
        for row in rows:
            by_token.setdefault(row["token"], set()).add(row["sku"])
        for token in tokens:
            skus = by_token.get(token)
            if not skus:
                continue
            if len(skus) > 1:
                logger.info("OCR token %s names %d products, skipping it", token, len(skus))
                continue
            return next(iter(skus))
        return None

    async def list_products(
        self,
        limit: int = 50,
        offset: int = 0,
        category: str | None = None,
        brand: str | None = None,
    ) -> list[dict[str, Any]]:
        """A page of the catalogue, optionally filtered.

        Ordered by SKU so paging is stable - without an explicit order the same
        row can appear on two pages or none.
        """
        query = sa.select(products)
        if category:
            query = query.where(products.c.category == category)
        if brand:
            query = query.where(products.c.brand == brand)
        query = query.order_by(products.c.sku).limit(limit).offset(offset)
        rows = (await self._session.execute(query)).mappings().all()
        return [self._to_dict(row) for row in rows]

    async def brands(self) -> list[str]:
        """Distinct brand names, alphabetically.

        Backs the "is this even a brand we stock" check, which is the only
        reliable way to rule out a part the catalogue does not carry - the
        photograph itself cannot. "Unknown" is excluded: it is the import's
        placeholder for missing data, not a brand a customer could pick.
        """
        rows = (await self._session.execute(
            sa.select(products.c.brand)
            .where(products.c.brand.isnot(None), products.c.brand != "Unknown")
            .distinct()
            .order_by(products.c.brand)
        )).scalars().all()
        return [b for b in rows if b and b.strip()]

    async def count(self) -> int:
        return int((await self._session.execute(
            sa.select(sa.func.count()).select_from(products)
        )).scalar_one())

    @staticmethod
    def _to_dict(row: Any) -> dict[str, Any]:
        attributes = row["attributes"] or {}
        return {
            "sku": row["sku"],
            "product_name": row["product_name"],
            "brand": row["brand"],
            "category": row["category"],
            "description": row["description"],
            "manufacturer_part_number": row["manufacturer_part_number"],
            "attributes": attributes,
            # RigidHitch's fitment is free text ("2 Inch Receivers", "Fisher
            # Compatible") rather than make/model/year, so it lives in
            # attributes rather than a structured column - surfaced here so
            # callers do not have to know that.
            "fitment": attributes.get("fitment"),
            "image_paths": row["image_paths"] or [],
            "images": _image_urls(row["image_paths"]),
        }
