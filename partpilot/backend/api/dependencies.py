"""FastAPI dependency providers.

Centralizes construction of pipeline services so route handlers depend
on interfaces (via `Depends(...)`) instead of instantiating concrete
classes themselves.

Brain 1/2 providers are cached process-wide singletons (`@lru_cache`):
construction is cheap today (placeholder objects) but will become
expensive once real models are loaded, which is exactly why we want a
single shared instance. Brain 3 providers are deliberately NOT cached —
they wrap a request-scoped `AsyncSession` (see `backend.core.database.get_db`)
and must be rebuilt on every request.
"""

from functools import lru_cache

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from backend.config.settings import Settings, get_settings
from backend.core.database import get_db
from backend.pipeline.brain1_classifier.interfaces import ClassifierInterface
from backend.pipeline.brain1_classifier.predict import Classifier
from backend.pipeline.brain2_similarity.interfaces import SimilaritySearchInterface
from backend.pipeline.brain2_similarity.search import SimilaritySearchService
from backend.pipeline.brain3_catalog.interfaces import RecommendationInterface
from backend.pipeline.brain3_catalog.product_service import ProductService
from backend.pipeline.brain3_catalog.recommendation_service import RecommendationService
from backend.pipeline.brain3_catalog.repository import ProductRepository
from backend.pipeline.brain4_reasoning.interfaces import ReasoningInterface
from backend.pipeline.brain4_reasoning.llm_service import LLMService
from backend.pipeline.orchestrator import PipelineOrchestrator


def get_app_settings() -> Settings:
    """Dependency provider for application settings."""
    return get_settings()


@lru_cache
def get_classifier() -> ClassifierInterface:
    """Dependency provider for the Brain 1 classifier."""
    return Classifier()


@lru_cache
def get_similarity_search() -> SimilaritySearchInterface:
    """Dependency provider for the Brain 2 similarity search service.

    Both stores hold the same vectors and return the same matches; the choice
    is where they live. `pgvector` keeps them in the product's own row, so they
    cannot drift out of step with the catalog, at the cost of a round trip per
    search. `faiss` reads them from index files on disk.
    """
    store = get_settings().VECTOR_STORE.strip().lower()
    if store == "pgvector":
        from backend.pipeline.brain2_similarity.pgvector_search import (  # noqa: PLC0415
            PgVectorSearchService,
        )

        return PgVectorSearchService()
    if store != "faiss":
        raise ValueError(f"Unknown VECTOR_STORE {store!r}; expected 'faiss' or 'pgvector'.")
    return SimilaritySearchService()


def get_product_repository(session: AsyncSession = Depends(get_db)) -> ProductRepository:
    """Dependency provider for the request-scoped Brain 3 product repository."""
    return ProductRepository(session)


def get_product_service(
    repository: ProductRepository = Depends(get_product_repository),
) -> ProductService:
    """Dependency provider for the Brain 3 product service."""
    return ProductService(repository)


def get_recommendation_service(
    product_service: ProductService = Depends(get_product_service),
) -> RecommendationInterface:
    """Dependency provider for the Brain 3 recommendation service."""
    return RecommendationService(catalog=product_service)


@lru_cache
def get_reasoning_service() -> ReasoningInterface:
    """Dependency provider for the Brain 4 (Qwen) reasoning service."""
    return LLMService()


def get_orchestrator(
    classifier: ClassifierInterface = Depends(get_classifier),
    similarity_search: SimilaritySearchInterface = Depends(get_similarity_search),
    catalog: ProductService = Depends(get_product_service),
    recommendation_service: RecommendationInterface = Depends(get_recommendation_service),
    reasoning: ReasoningInterface = Depends(get_reasoning_service),
) -> PipelineOrchestrator:
    """Dependency provider for the full pipeline orchestrator."""
    return PipelineOrchestrator(
        classifier=classifier,
        similarity_search=similarity_search,
        catalog=catalog,
        recommendation_service=recommendation_service,
        reasoning=reasoning,
    )
