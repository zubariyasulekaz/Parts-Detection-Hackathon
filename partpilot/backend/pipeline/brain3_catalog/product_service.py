"""Product Catalog Service.

The ONLY module Brain 3 consumers (the `/products` API, the pipeline
orchestrator, and future AI modules) should call to read or write
product data. Wraps `ProductRepository`, translating ORM instances
to/from the public Pydantic schemas and raising domain exceptions
instead of leaking SQLAlchemy internals to callers. Contains no direct
database access — see `ProductRepository` for that.
"""

from backend.core.exceptions import ProductAlreadyExists, ProductNotFound
from backend.core.logging import get_logger
from backend.pipeline.brain3_catalog.interfaces import CatalogInterface
from backend.pipeline.brain3_catalog.repository import ProductRepository
from backend.schemas.catalog import ProductCreate, ProductResponse, ProductUpdate

logger = get_logger(__name__)


class ProductService(CatalogInterface):
    """Business-facing product catalog service.

    Args:
        repository: Async repository providing raw DB access. Injected
            per-request via `backend.api.dependencies.get_product_service`.
    """

    def __init__(self, repository: ProductRepository) -> None:
        self._repository = repository

    async def create_product(self, data: ProductCreate) -> ProductResponse:
        """Create a new catalog product.

        Args:
            data: Validated product payload, including its SKU.

        Returns:
            The newly created product.

        Raises:
            backend.core.exceptions.ProductAlreadyExists: If `data.sku`
                is already in use.
        """
        if await self._repository.exists(data.sku):
            raise ProductAlreadyExists(f"Product with SKU '{data.sku}' already exists.")
        product = await self._repository.create(data)
        logger.info("Product created: sku=%s", product.sku)
        return ProductResponse.model_validate(product)

    async def update_product(self, sku: str, data: ProductUpdate) -> ProductResponse:
        """Partially update an existing catalog product.

        Raises:
            backend.core.exceptions.ProductNotFound: If `sku` is unknown.
        """
        product = await self._repository.update(sku, data)
        if product is None:
            raise ProductNotFound(f"Product with SKU '{sku}' was not found.")
        logger.info("Product updated: sku=%s", product.sku)
        return ProductResponse.model_validate(product)

    async def delete_product(self, sku: str) -> None:
        """Delete a catalog product.

        Raises:
            backend.core.exceptions.ProductNotFound: If `sku` is unknown.
        """
        deleted = await self._repository.delete(sku)
        if not deleted:
            raise ProductNotFound(f"Product with SKU '{sku}' was not found.")
        logger.info("Product deleted: sku=%s", sku)

    async def get_product(self, sku: str) -> ProductResponse:
        """Fetch a single product by SKU.

        Raises:
            backend.core.exceptions.ProductNotFound: If `sku` is unknown.
        """
        product = await self._repository.get_by_sku(sku)
        if product is None:
            raise ProductNotFound(f"Product with SKU '{sku}' was not found.")
        logger.info("Product retrieved: sku=%s", sku)
        return ProductResponse.model_validate(product)

    async def list_products(self, limit: int = 50, offset: int = 0) -> list[ProductResponse]:
        """List catalog products with pagination."""
        products = await self._repository.get_all(limit=limit, offset=offset)
        return [ProductResponse.model_validate(p) for p in products]

    async def search_by_category(self, category: str, limit: int = 50) -> list[ProductResponse]:
        """List products belonging to a given category."""
        products = await self._repository.get_by_category(category, limit=limit)
        return [ProductResponse.model_validate(p) for p in products]

    async def search_by_brand(self, brand: str, limit: int = 50) -> list[ProductResponse]:
        """List products from a given brand."""
        products = await self._repository.get_by_brand(brand, limit=limit)
        return [ProductResponse.model_validate(p) for p in products]

    async def exists(self, sku: str) -> bool:
        """Return whether a product with `sku` exists."""
        return await self._repository.exists(sku)

    async def count(self) -> int:
        """Return the total number of products in the catalog."""
        return await self._repository.count()
