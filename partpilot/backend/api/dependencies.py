"""FastAPI dependency providers.

Centralizes construction of pipeline services so route handlers depend on
interfaces (via `Depends(...)`) instead of instantiating concrete classes
themselves.

The search service is a process-wide singleton (`@lru_cache`): it holds a
330 MB fine-tuned model and a FAISS index, so a second instance would double
the memory for no benefit. The catalogue is deliberately NOT cached - it wraps
a request-scoped `AsyncSession` (see `backend.core.database.get_rigidhitch_db`)
and must be rebuilt on every request.
"""

from functools import lru_cache
from pathlib import Path

from backend.config.settings import Settings, get_settings
from backend.pipeline.brain2_similarity.index_manager import IndexManager
from backend.pipeline.brain2_similarity.search import SimilaritySearchService


def get_app_settings() -> Settings:
    """Dependency provider for application settings."""
    return get_settings()


@lru_cache
def get_rigidhitch_search() -> SimilaritySearchService:
    """Similarity search for the RigidHitch catalogue.

    `IndexManager` takes the index directory rather than reading the default,
    because RigidHitch's index lives in its own folder alongside the whitening
    transform and the sidecar recording which model built it.

    The whitening transform travels with the index file, so nothing here needs
    to know that RigidHitch's vectors are whitened.
    """
    settings = get_settings()
    return SimilaritySearchService(
        index_manager=IndexManager(Path(settings.RIGIDHITCH_FAISS_PATH))
    )
