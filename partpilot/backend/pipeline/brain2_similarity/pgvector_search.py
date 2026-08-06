"""`SimilaritySearchInterface` implementation backed by pgvector.

Same job as the FAISS implementation - embed the query image, find the nearest
catalog vectors in that category - except the vectors live in the products
table rather than in index files on disk.

The reason to prefer this is not speed; it is that a vector stored in the
product's own row cannot drift away from it. With index files, renaming the
SKUs left the indexes pointing at names the catalog no longer had, and nothing
raised an error - matches simply resolved to products that did not exist.

Which model to embed the query with comes from the rows themselves. Each row
records the backend that produced its vector, and comparing vectors from
different models does not fail loudly - it returns confident nonsense - so the
model is read from the data rather than assumed from configuration.

Runs its query through a synchronous connection because
`SimilaritySearchInterface.search` is synchronous while the application engine
is async. A short-lived psycopg2 connection per search is fine at this scale
and avoids making the whole pipeline async for one query.
"""

from PIL.Image import Image
from sqlalchemy import create_engine, text

from backend.config.settings import get_settings
from backend.core.exceptions import SearchError
from backend.core.logging import get_logger
from backend.pipeline.brain2_similarity.embedding_backends import (
    BackendCache,
    backend_for_category,
)
from backend.pipeline.brain2_similarity.embedding_generator import EmbeddingGenerator
from backend.pipeline.brain2_similarity.interfaces import (
    SimilarityMatch,
    SimilaritySearchInterface,
)

logger = get_logger(__name__)

#: Vector length -> the column holding vectors of that length.
DIM_COLUMN = {768: "embedding_768", 512: "embedding_512"}


class PgVectorSearchService(SimilaritySearchInterface):
    """Finds visually similar SKUs by querying pgvector."""

    def __init__(self, database_url: str | None = None) -> None:
        settings = get_settings()
        url = database_url or settings.DATABASE_URL
        # The app engine is asyncpg; this needs a sync driver.
        self._engine = create_engine(
            url.replace("postgresql+asyncpg", "postgresql+psycopg2"),
            pool_pre_ping=True,
        )
        self._backends = BackendCache()
        self._generators: dict[str, EmbeddingGenerator] = {}

    def _generator_for(self, spec: str) -> EmbeddingGenerator:
        if spec not in self._generators:
            self._generators[spec] = EmbeddingGenerator(backend=self._backends.get(spec))
        return self._generators[spec]

    def _stored_backend(self, connection, category: str) -> str | None:
        """Which model produced the vectors stored for this category."""
        row = connection.execute(
            text(
                "SELECT embedding_backend, COUNT(*) AS n FROM products "
                "WHERE lower(category) = lower(:category) "
                "AND embedding_backend IS NOT NULL "
                "GROUP BY embedding_backend ORDER BY n DESC LIMIT 1"
            ),
            {"category": category.strip()},
        ).first()
        return row[0] if row else None

    def search(
        self,
        category: str,
        image: Image,
        top_k: int | None = None,
    ) -> list[SimilarityMatch]:
        """Find the top-K most visually similar SKUs within a category.

        Raises:
            backend.core.exceptions.EmbeddingError: If embedding fails.
            backend.core.exceptions.SearchError: If the category has no stored
                vectors or the query fails.
        """
        top_k = top_k or get_settings().FAISS_TOP_K

        with self._engine.connect() as connection:
            spec = self._stored_backend(connection, category) or backend_for_category(category)
            embedding = self._generator_for(spec).generate(image)

            column = DIM_COLUMN.get(embedding.shape[0])
            if column is None:
                raise SearchError(
                    f"{spec} produced {embedding.shape[0]}-dim vectors, which have no column. "
                    f"Expected one of: {sorted(DIM_COLUMN)}."
                )

            # pgvector's <=> is cosine distance, so 1 - distance is cosine
            # similarity - the same score IndexFlatIP returns for these
            # L2-normalized vectors.
            literal = "[" + ",".join(f"{v:.8f}" for v in embedding) + "]"
            rows = connection.execute(
                text(
                    f"SELECT sku, 1 - ({column} <=> CAST(:query AS vector)) AS similarity "
                    f"FROM products "
                    f"WHERE lower(category) = lower(:category) AND {column} IS NOT NULL "
                    f"ORDER BY {column} <=> CAST(:query AS vector) "
                    f"LIMIT :top_k"
                ),
                {"query": literal, "category": category.strip(), "top_k": top_k},
            ).all()

        if not rows:
            raise SearchError(
                f"No stored vectors for category '{category}'. "
                "Run scripts/load_embeddings_to_db.py."
            )

        logger.info("pgvector matched %d products in '%s' using %s", len(rows), category, spec)
        return [SimilarityMatch(sku=sku, similarity_score=float(score)) for sku, score in rows]
