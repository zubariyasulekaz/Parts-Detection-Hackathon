"""Concrete `SimilaritySearchInterface` implementation.

Chains embedding generation (OpenCLIP) with a category-scoped FAISS
lookup (via `IndexManager`).
"""

from PIL.Image import Image

from backend.config.settings import get_settings
from backend.core.logging import get_logger
from backend.pipeline.brain2_similarity.embedding_generator import EmbeddingGenerator
from backend.pipeline.brain2_similarity.index_manager import IndexManager
from backend.pipeline.brain2_similarity.interfaces import (
    EmbeddingGeneratorInterface,
    SimilarityMatch,
    SimilaritySearchInterface,
)

logger = get_logger(__name__)


class SimilaritySearchService(SimilaritySearchInterface):
    """Finds visually similar SKUs for a classified part image."""

    def __init__(
        self,
        embedding_generator: EmbeddingGeneratorInterface | None = None,
        index_manager: IndexManager | None = None,
    ) -> None:
        self._embedding_generator = embedding_generator or EmbeddingGenerator()
        self._index_manager = index_manager or IndexManager()

    def search(
        self,
        category: str,
        image: Image,
        top_k: int | None = None,
    ) -> list[SimilarityMatch]:
        """Find the top-K most visually similar SKUs within a category.

        Raises:
            backend.core.exceptions.EmbeddingError: If embedding fails.
            backend.core.exceptions.SearchError: If no index exists for the
                category or the search fails.
        """
        top_k = top_k or get_settings().FAISS_TOP_K
        embedding = self._embedding_generator.generate(image)
        index = self._index_manager.get_index(category)
        raw_matches = index.search(embedding, top_k)
        return [SimilarityMatch(sku=sku, similarity_score=score) for sku, score in raw_matches]
