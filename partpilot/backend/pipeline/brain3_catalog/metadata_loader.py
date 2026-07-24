"""Loads raw catalog metadata from disk into memory/an index structure.

TODO: Implement actual catalog ingestion. At 100k+ product scale this
likely means loading from a columnar format (Parquet) or a proper
database rather than a single JSON/CSV file, with an in-memory SKU ->
record index for O(1) lookups.
"""

from pathlib import Path
from typing import Any

from backend.config.settings import get_settings
from backend.core.exceptions import CatalogError
from backend.core.logging import get_logger

logger = get_logger(__name__)


class MetadataLoader:
    """Loads catalog records and exposes SKU-indexed lookups."""

    def __init__(self, catalog_path: Path | None = None) -> None:
        self._catalog_path = catalog_path or Path(get_settings().CATALOG_PATH)
        self._records_by_sku: dict[str, dict[str, Any]] | None = None

    @property
    def is_loaded(self) -> bool:
        """Whether catalog records have been loaded into memory."""
        return self._records_by_sku is not None

    def load(self) -> None:
        """Load all catalog records from `self._catalog_path`.

        TODO: Implement parsing (CSV/JSON/Parquet) and build the
        `sku -> record` index.
        """
        raise NotImplementedError("Catalog metadata loading is not implemented yet.")

    def get_record(self, sku: str) -> dict[str, Any]:
        """Return the raw metadata record for a SKU.

        Raises:
            backend.core.exceptions.CatalogError: If the catalog has not
                been loaded, or `sku` is unknown.
        """
        if self._records_by_sku is None:
            raise CatalogError("Catalog metadata has not been loaded.")
        try:
            return self._records_by_sku[sku]
        except KeyError as exc:
            raise CatalogError(f"Unknown SKU: {sku}") from exc
