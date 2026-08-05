"""Concrete `SimilaritySearchInterface` implementation.

Embeds the query image and looks for the nearest catalog vectors in that
category's FAISS index.

Which model does the embedding can differ per category. Benchmarking on the
catalog showed no single model wins everywhere - DINOv2 is far better on parts
that differ structurally (brake pads, exhaust manifolds) while OpenCLIP holds up
better where every product shares the same texture (air filters, wheel hubs).
Since each category already has its own index, each can be built by whichever
model scored best for it.

The query must be embedded by the same model that built the index, or the
vectors are not comparable. The index records its backend when it is written,
so that is what we follow; the configured setting is only a fallback for older
indexes saved before this was tracked.
"""

from PIL.Image import Image

from backend.config.settings import get_settings
from backend.core.logging import get_logger
from backend.pipeline.brain2_similarity.embedding_backends import (
    BackendCache,
    backend_for_category,
)
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
        """
        Args:
            embedding_generator: Force one generator for every category
                (mainly for tests). By default the model is chosen per
                category.
            index_manager: Override the FAISS index manager.
        """
        self._fixed_generator = embedding_generator
        self._index_manager = index_manager or IndexManager()
        self._backends = BackendCache()
        self._generators: dict[str, EmbeddingGenerator] = {}

    def _generator_for(self, spec: str) -> EmbeddingGeneratorInterface:
        """Cached generator for a backend spec (models are slow to load)."""
        if self._fixed_generator is not None:
            return self._fixed_generator
        if spec not in self._generators:
            self._generators[spec] = EmbeddingGenerator(backend=self._backends.get(spec))
        return self._generators[spec]

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
        index = self._index_manager.get_index(category)

        # Follow the index's own backend so the query matches how it was built.
        spec = index.backend or backend_for_category(category)
        embedding = self._generator_for(spec).generate(image)

        raw_matches = index.search(embedding, top_k)
        return [SimilarityMatch(sku=sku, similarity_score=score) for sku, score in raw_matches]
