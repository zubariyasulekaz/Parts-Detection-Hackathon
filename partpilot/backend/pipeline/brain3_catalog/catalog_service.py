"""Concrete `CatalogInterface` implementation backed by `MetadataLoader`."""

from backend.core.logging import get_logger
from backend.pipeline.brain3_catalog.interfaces import CatalogInterface
from backend.pipeline.brain3_catalog.metadata_loader import MetadataLoader
from backend.schemas.catalog import Product

logger = get_logger(__name__)


class CatalogService(CatalogInterface):
    """Reads and serves catalog metadata."""

    def __init__(self, metadata_loader: MetadataLoader | None = None) -> None:
        self._metadata_loader = metadata_loader or MetadataLoader()

    def get_product(self, sku: str) -> Product:
        """Fetch full catalog metadata for a single SKU.

        TODO:
            1. `record = self._metadata_loader.get_record(sku)`.
            2. Map the raw record dict to a `Product` schema instance.
        """
        raise NotImplementedError("Brain 3 CatalogService.get_product is not implemented yet.")

    def search_by_category(self, category: str, limit: int = 50) -> list[Product]:
        """List products belonging to a given category.

        TODO: Implement a category -> [sku] index in `MetadataLoader`
        (or a dedicated search structure) for efficient lookups at scale.
        """
        raise NotImplementedError(
            "Brain 3 CatalogService.search_by_category is not implemented yet."
        )
