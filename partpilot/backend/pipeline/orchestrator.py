"""Pipeline orchestrator: chains Brain 1 -> Brain 2 -> Brain 3 -> Brain 4.

The orchestrator itself contains no AI logic — it is pure
composition/wiring, following dependency inversion (it depends on the
`*Interface` ABCs, never concrete classes). See `backend.api.dependencies`
for how concrete implementations are constructed and injected.
"""

from dataclasses import dataclass
from time import perf_counter

from PIL.Image import Image

from backend.core.logging import get_logger
from backend.pipeline.brain1_classifier.interfaces import ClassifierInterface
from backend.pipeline.brain1_classifier.labels import resolve_catalog_category
from backend.pipeline.brain2_similarity.interfaces import SimilaritySearchInterface
from backend.pipeline.brain3_catalog.interfaces import (
    CatalogInterface,
    RecommendationInterface,
)
from backend.pipeline.brain4_reasoning.interfaces import ReasoningInterface
from backend.schemas.catalog import Product
from backend.schemas.prediction import PredictionResponse, SearchResult
from backend.schemas.recommendation import Recommendation

logger = get_logger(__name__)


@dataclass
class OrchestratorResult:
    """Aggregated output of a full pipeline run."""

    prediction: PredictionResponse
    product: Product | None = None
    recommendation: Recommendation | None = None
    explanation: str | None = None


class PipelineOrchestrator:
    """Coordinates the four pipeline stages (Brains 1-4).

    Each stage is injected as an interface so concrete implementations
    can be swapped (or mocked in tests) without changing this class. See
    `backend.api.dependencies` for how instances are constructed and
    wired into FastAPI request handlers.
    """

    def __init__(
        self,
        classifier: ClassifierInterface,
        similarity_search: SimilaritySearchInterface,
        catalog: CatalogInterface,
        recommendation_service: RecommendationInterface,
        reasoning: ReasoningInterface | None = None,
    ) -> None:
        self._classifier = classifier
        self._similarity_search = similarity_search
        self._catalog = catalog
        self._recommendation_service = recommendation_service
        # Brain 4 is optional/future — the pipeline must function without it.
        self._reasoning = reasoning

    async def run(
        self,
        image: Image,
        top_k: int = 10,
        explain: bool = False,
        remove_bg: bool = True,
    ) -> OrchestratorResult:
        """Execute the full identification pipeline for a single image.

        Flow:
            Image -> (rembg background removal) -> Brain 1 (classify)
                  -> Brain 2 (similarity search within the category)
                  -> Brain 3 (catalog lookup + recommendations)
                  -> Brain 4 (optional LLM explanation)

        Background removal is applied once, up front, so both the classifier
        and the similarity search operate on the same cleaned image (and so
        it matches how the catalog embeddings were built).

        Args:
            image: Decoded part image to identify.
            top_k: Number of similar SKUs to retrieve from Brain 2.
            explain: Whether to additionally invoke Brain 4 for a
                natural-language explanation. Ignored (no-op) until
                Brain 4 is implemented.
            remove_bg: Whether to strip the image background with rembg
                before classification/search.

        Returns:
            An `OrchestratorResult` aggregating every stage's output.

        Raises:
            backend.core.exceptions.PredictionError: If any required
                stage fails.
        """
        start = perf_counter()

        # Stage 0: strip the background so the part stands alone.
        if remove_bg:
            from backend.utils.image_utils import remove_background  # lazy: heavy dep

            image = remove_background(image)

        # Stage 1: classify the image into a category.
        classification = self._classifier.predict(image)
        # Map the classifier label to the catalog category (e.g.
        # "brake_pad" -> "Brake Pads") used for the FAISS index + catalog.
        category = resolve_catalog_category(classification.category)

        # Stage 2: search for visually similar SKUs within that category.
        matches = self._similarity_search.search(
            category=category, image=image, top_k=top_k
        )
        search_results = [
            SearchResult(sku=m.sku, similarity_score=m.similarity_score) for m in matches
        ]

        elapsed_ms = (perf_counter() - start) * 1000
        prediction = PredictionResponse(
            predicted_category=category,
            confidence=classification.confidence,
            search_time_ms=elapsed_ms,
            results=search_results,
        )

        # Stage 3: resolve the top match to full catalog metadata + recommendations.
        # TODO: Decide the confidence/similarity threshold below which we
        # skip catalog lookup entirely (no confident SKU match).
        product: Product | None = None
        recommendation: Recommendation | None = None
        if search_results:
            top_sku = search_results[0].sku
            product = await self._catalog.get_product(top_sku)
            recommendation = await self._recommendation_service.recommend(top_sku)

        # Stage 4 (optional, future): LLM-generated explanation.
        explanation: str | None = None
        if explain and self._reasoning is not None:
            explanation = self._reasoning.explain(prediction, product, recommendation)

        return OrchestratorResult(
            prediction=prediction,
            product=product,
            recommendation=recommendation,
            explanation=explanation,
        )
