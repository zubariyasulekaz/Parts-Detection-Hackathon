"""FastAPI dependency providers.

Centralizes construction of pipeline services so route handlers depend
on interfaces (via `Depends(...)`) instead of instantiating concrete
classes themselves. Every provider below is a cached singleton for the
lifetime of the process — construction is cheap today (placeholder
objects) but will become expensive once real models are loaded, which
is exactly why we want a single shared instance.
"""

from functools import lru_cache

from backend.config.settings import Settings, get_settings
from backend.pipeline.brain1_classifier.interfaces import ClassifierInterface
from backend.pipeline.brain1_classifier.predict import Classifier
from backend.pipeline.brain2_similarity.interfaces import SimilaritySearchInterface
from backend.pipeline.brain2_similarity.search import SimilaritySearchService
from backend.pipeline.brain3_catalog.catalog_service import CatalogService
from backend.pipeline.brain3_catalog.interfaces import (
    CatalogInterface,
    RecommendationInterface,
)
from backend.pipeline.brain3_catalog.recommendation_service import RecommendationService
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
    """Dependency provider for the Brain 2 similarity search service."""
    return SimilaritySearchService()


@lru_cache
def get_catalog_service() -> CatalogInterface:
    """Dependency provider for the Brain 3 catalog service."""
    return CatalogService()


@lru_cache
def get_recommendation_service() -> RecommendationInterface:
    """Dependency provider for the Brain 3 recommendation service."""
    return RecommendationService(catalog=get_catalog_service())


@lru_cache
def get_orchestrator() -> PipelineOrchestrator:
    """Dependency provider for the full pipeline orchestrator.

    TODO: Once Brain 4 is implemented, wire a `ReasoningInterface`
    instance through here as well.
    """
    return PipelineOrchestrator(
        classifier=get_classifier(),
        similarity_search=get_similarity_search(),
        catalog=get_catalog_service(),
        recommendation_service=get_recommendation_service(),
        reasoning=None,
    )
