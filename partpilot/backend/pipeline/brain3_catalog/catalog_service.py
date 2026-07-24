"""Concrete `CatalogInterface` implementation backed by `MetadataLoader`."""

from typing import Any

from backend.core.logging import get_logger
from backend.pipeline.brain3_catalog.interfaces import CatalogInterface
from backend.pipeline.brain3_catalog.metadata_loader import MetadataLoader
from backend.schemas.catalog import Product

logger = get_logger(__name__)

#: Separator used for multi-valued CSV columns (compatible_vehicles, accessory_skus).
_LIST_SEPARATOR = "|"


def _split_list(value: str | None) -> list[str]:
    """Parse a pipe-separated CSV cell into a list of trimmed, non-empty items."""
    if not value:
        return []
    return [item.strip() for item in value.split(_LIST_SEPARATOR) if item.strip()]


def _clean_optional(value: str | None) -> str | None:
    """Return a trimmed string, or None if the cell is empty/whitespace."""
    if value is None:
        return None
    value = value.strip()
    return value or None


def _record_to_product(record: dict[str, Any]) -> Product:
    """Map a raw catalog CSV record to a `Product` schema instance."""
    return Product(
        sku=(record.get("sku") or "").strip(),
        product_name=(record.get("product_name") or "").strip(),
        brand=(record.get("brand") or "").strip(),
        category=(record.get("category") or "").strip(),
        description=(record.get("description") or "").strip(),
        compatible_vehicles=_split_list(record.get("compatible_vehicles")),
        replacement_sku=_clean_optional(record.get("replacement_sku")),
        alternative_sku=_clean_optional(record.get("alternative_sku")),
        accessory_skus=_split_list(record.get("accessory_skus")),
    )


class CatalogService(CatalogInterface):
    """Reads and serves catalog metadata."""

    def __init__(self, metadata_loader: MetadataLoader | None = None) -> None:
        self._metadata_loader = metadata_loader or MetadataLoader()

    def get_product(self, sku: str) -> Product:
        """Fetch full catalog metadata for a single SKU.

        Raises:
            backend.core.exceptions.CatalogError: If the SKU is unknown or
                the catalog cannot be read.
        """
        record = self._metadata_loader.get_record(sku)
        return _record_to_product(record)

    def search_by_category(self, category: str, limit: int = 50) -> list[Product]:
        """List products belonging to a given category."""
        records = self._metadata_loader.get_records_by_category(category, limit=limit)
        return [_record_to_product(record) for record in records]
