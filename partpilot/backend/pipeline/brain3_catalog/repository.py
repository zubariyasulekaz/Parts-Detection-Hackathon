"""Product catalog repository.

The ONLY module in Brain 3 allowed to talk to the database. Every
method here is a thin, typed wrapper around a SQLAlchemy statement —
no business rules (uniqueness checks, error translation, logging of
domain events) belong in this class. See `ProductService` for that.
"""

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.logging import get_logger
from backend.pipeline.brain3_catalog.models import Product as ProductORM
from backend.schemas.catalog import ProductCreate, ProductUpdate

logger = get_logger(__name__)


class ProductRepository:
    """Async CRUD access to the `products` table.

    Args:
        session: Request-scoped `AsyncSession`, injected via
            `backend.api.dependencies.get_product_repository`.
    """

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(self, data: ProductCreate) -> ProductORM:
        """Insert a new product row.

        Args:
            data: Validated product payload.

        Returns:
            The persisted ORM instance, refreshed so DB-generated
            fields (`created_at`, `updated_at`) are populated.
        """
        product = ProductORM(**data.model_dump())
        self._session.add(product)
        await self._session.flush()
        await self._session.refresh(product)
        return product

    async def update(self, sku: str, data: ProductUpdate) -> ProductORM | None:
        """Apply a partial update to an existing product.

        Args:
            sku: Primary key of the product to update.
            data: Fields to update; unset fields are left untouched.

        Returns:
            The updated ORM instance, or `None` if `sku` does not exist.
        """
        product = await self.get_by_sku(sku)
        if product is None:
            return None

        for field, value in data.model_dump(exclude_unset=True).items():
            setattr(product, field, value)

        await self._session.flush()
        await self._session.refresh(product)
        return product

    async def delete(self, sku: str) -> bool:
        """Delete a product by SKU.

        Returns:
            `True` if a row was deleted, `False` if `sku` did not exist.
        """
        product = await self.get_by_sku(sku)
        if product is None:
            return False
        await self._session.delete(product)
        await self._session.flush()
        return True

    async def get_by_sku(self, sku: str) -> ProductORM | None:
        """Fetch a single product by its primary key."""
        return await self._session.get(ProductORM, sku)

    async def get_all(self, limit: int = 50, offset: int = 0) -> list[ProductORM]:
        """List products, ordered by SKU, with pagination."""
        stmt = select(ProductORM).order_by(ProductORM.sku).limit(limit).offset(offset)
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def get_by_category(
        self, category: str, limit: int = 50, offset: int = 0
    ) -> list[ProductORM]:
        """List products in a given category, with pagination."""
        stmt = (
            select(ProductORM)
            .where(ProductORM.category == category)
            .order_by(ProductORM.sku)
            .limit(limit)
            .offset(offset)
        )
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def get_by_brand(self, brand: str, limit: int = 50, offset: int = 0) -> list[ProductORM]:
        """List products from a given brand, with pagination."""
        stmt = (
            select(ProductORM)
            .where(ProductORM.brand == brand)
            .order_by(ProductORM.sku)
            .limit(limit)
            .offset(offset)
        )
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def exists(self, sku: str) -> bool:
        """Return whether a product with `sku` exists."""
        stmt = select(func.count()).select_from(ProductORM).where(ProductORM.sku == sku)
        result = await self._session.execute(stmt)
        return (result.scalar_one() or 0) > 0

    async def count(self) -> int:
        """Return the total number of products in the catalog."""
        stmt = select(func.count()).select_from(ProductORM)
        result = await self._session.execute(stmt)
        return result.scalar_one()
