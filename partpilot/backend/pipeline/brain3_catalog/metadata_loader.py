"""Loads raw catalog metadata from a CSV file into memory.

For the prototype the catalog is a single ``catalog.csv`` (see
``datasets/catalog.csv``) small enough to hold entirely in memory with a
``sku -> record`` index for O(1) lookups and a ``category -> [sku]`` index
for category listings.

TODO: At 100k+ product scale this likely means loading from a columnar
format (Parquet) or a proper database rather than a single CSV file.
"""

import csv
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
        self._skus_by_category: dict[str, list[str]] = {}

    @property
    def is_loaded(self) -> bool:
        """Whether catalog records have been loaded into memory."""
        return self._records_by_sku is not None

    def _resolve_csv_path(self) -> Path:
        """Return the CSV file path, allowing the configured path to be a dir."""
        path = self._catalog_path
        if path.is_dir():
            path = path / "catalog.csv"
        if not path.is_file():
            raise CatalogError(f"Catalog CSV not found: {path}")
        return path

    def load(self) -> None:
        """Load all catalog records from the configured CSV file.

        Idempotent: calling this repeatedly re-reads the file and rebuilds
        the in-memory indexes. Rows without a ``sku`` are skipped.

        Raises:
            backend.core.exceptions.CatalogError: If the file is missing or
                cannot be parsed.
        """
        csv_path = self._resolve_csv_path()
        records_by_sku: dict[str, dict[str, Any]] = {}
        skus_by_category: dict[str, list[str]] = {}

        try:
            with csv_path.open("r", newline="", encoding="utf-8-sig") as f:
                reader = csv.DictReader(f)
                for line_no, row in enumerate(reader, start=2):
                    sku = (row.get("sku") or "").strip()
                    if not sku:
                        logger.warning("Skipping catalog row %d with empty sku", line_no)
                        continue
                    if sku in records_by_sku:
                        logger.warning("Duplicate sku %s at row %d; overwriting", sku, line_no)
                    records_by_sku[sku] = row
                    category = (row.get("category") or "").strip()
                    if category:
                        skus_by_category.setdefault(category, []).append(sku)
        except OSError as exc:
            raise CatalogError(f"Failed to read catalog CSV {csv_path}: {exc}") from exc

        self._records_by_sku = records_by_sku
        self._skus_by_category = skus_by_category
        logger.info(
            "Loaded %d catalog records across %d categories from %s",
            len(records_by_sku),
            len(skus_by_category),
            csv_path,
        )

    def _ensure_loaded(self) -> None:
        if self._records_by_sku is None:
            self.load()

    def get_record(self, sku: str) -> dict[str, Any]:
        """Return the raw metadata record for a SKU.

        Loads the catalog on first access.

        Raises:
            backend.core.exceptions.CatalogError: If `sku` is unknown.
        """
        self._ensure_loaded()
        assert self._records_by_sku is not None  # for type-checkers
        try:
            return self._records_by_sku[sku]
        except KeyError as exc:
            raise CatalogError(f"Unknown SKU: {sku}") from exc

    def get_records_by_category(self, category: str, limit: int | None = None) -> list[dict[str, Any]]:
        """Return raw records for a category (case-insensitive), up to `limit`."""
        self._ensure_loaded()
        assert self._records_by_sku is not None
        # Case-insensitive category match.
        match = next(
            (skus for cat, skus in self._skus_by_category.items()
             if cat.lower() == category.strip().lower()),
            [],
        )
        skus = match if limit is None else match[:limit]
        return [self._records_by_sku[sku] for sku in skus]
