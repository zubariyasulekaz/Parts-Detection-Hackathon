"""Pipeline orchestrator: chains Brain 1 -> Brain 2 -> Brain 3 -> Brain 4.

The orchestrator itself contains no AI logic — it is pure
composition/wiring, following dependency inversion (it depends on the
`*Interface` ABCs, never concrete classes). See `backend.api.dependencies`
for how concrete implementations are constructed and injected.
"""

from dataclasses import dataclass
from time import perf_counter

from fastapi.concurrency import run_in_threadpool
from PIL.Image import Image

from backend.config.settings import get_settings
from backend.core.exceptions import SearchError
from backend.core.logging import get_logger
from backend.pipeline.brain1_classifier.interfaces import ClassifierInterface
from backend.pipeline.brain1_classifier.labels import resolve_catalog_category
from backend.pipeline.brain2_similarity.embedding_backends import no_match_threshold
from backend.pipeline.brain2_similarity.interfaces import (
    SearchOutcome,
    SimilaritySearchInterface,
)
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


@dataclass
class _ModelStageResult:
    """Everything the sync model stages (Brains 1-2) produce."""

    category: str
    category_confidence: float
    outcome: SearchOutcome
    threshold: float
    searched_categories: list[str]
    elapsed_ms: float
    # Brain 1 was below its confidence threshold — the no-match bar rises.
    classifier_uncertain: bool = False


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
                  -> Brain 2 (similarity search within the category — or the
                     top-2 categories when the classifier is uncertain)
                  -> no-match verdict against the per-backend threshold
                  -> Brain 3 (catalog lookup + recommendations, skipped on
                     no-match)
                  -> Brain 4 (optional LLM explanation)

        The model stages are synchronous CPU work (rembg, TensorFlow, a
        vision transformer), so they run in the threadpool rather than
        blocking the event loop for the whole inference.

        Args:
            image: Decoded part image to identify.
            top_k: Number of similar SKUs to retrieve from Brain 2.
            explain: Whether to additionally invoke Brain 4 for a
                natural-language explanation.
            remove_bg: Whether to strip the image background with rembg
                before classification/search.

        Returns:
            An `OrchestratorResult` aggregating every stage's output.

        Raises:
            backend.core.exceptions.PredictionError: If any required
                stage fails.
        """
        stage = await run_in_threadpool(self._run_model_stages, image, top_k, remove_bg)

        # An uncertain classifier raises the bar: "unsure what kind of part"
        # plus "nothing especially close in that category" must not combine
        # into a confidently named SKU. Refusing beats guessing.
        threshold = stage.threshold
        if stage.classifier_uncertain:
            threshold += get_settings().NO_MATCH_UNCERTAIN_MARGIN

        top_score = (
            stage.outcome.matches[0].similarity_score if stage.outcome.matches else None
        )
        no_match = top_score is None or top_score < threshold
        if no_match:
            logger.info(
                "No catalog match: top similarity %s vs threshold %.2f (%s%s)",
                f"{top_score:.3f}" if top_score is not None else "n/a",
                threshold,
                stage.outcome.backend,
                ", classifier uncertain" if stage.classifier_uncertain else "",
            )

        prediction = PredictionResponse(
            predicted_category=stage.category,
            confidence=stage.category_confidence,
            search_time_ms=stage.elapsed_ms,
            results=[
                SearchResult(sku=m.sku, similarity_score=m.similarity_score)
                for m in stage.outcome.matches
            ],
            no_match=no_match,
            no_match_threshold=threshold,
            embedding_backend=stage.outcome.backend,
            searched_categories=stage.searched_categories,
        )

        # Stage 3: resolve the top match to full catalog metadata +
        # recommendations — but only when it cleared the threshold. Below it,
        # naming the nearest wrong part with a confident product page is
        # worse than an honest "not in our catalog".
        product: Product | None = None
        recommendation: Recommendation | None = None
        if prediction.results and not no_match:
            top_sku = prediction.results[0].sku
            product = await self._catalog.get_product(top_sku)
            recommendation = await self._recommendation_service.recommend(top_sku)

        # Stage 4 (optional): LLM-generated explanation. Brain 4 is a
        # nice-to-have on top of an already-complete answer, so a failure
        # here (model weights unreachable, generation error) must not cost
        # the caller the Brain 1-3 result. Degrade to no explanation. Runs
        # in the threadpool: generation takes seconds of sync CPU time.
        explanation: str | None = None
        if explain and self._reasoning is not None:
            try:
                explanation = await run_in_threadpool(
                    self._reasoning.explain, prediction, product, recommendation
                )
            except Exception as exc:  # noqa: BLE001
                logger.warning("Brain 4 unavailable; returning result without an explanation: %s", exc)

        return OrchestratorResult(
            prediction=prediction,
            product=product,
            recommendation=recommendation,
            explanation=explanation,
        )

    def _run_model_stages(self, image: Image, top_k: int, remove_bg: bool) -> _ModelStageResult:
        """Run the synchronous model stages: rembg, Brain 1, Brain 2.

        When the classifier's confidence falls below
        ``CLASSIFIER_CONFIDENCE_THRESHOLD``, the runner-up category is
        searched as well — a wrong hard gate at Brain 1 is otherwise
        unrecoverable, since Brain 2 only looks inside one index. The
        winner is the category whose top match clears its backend's
        no-match threshold by the most (scores from different backends are
        not directly comparable, so the margin over each one's own
        threshold is compared instead).
        """
        start = perf_counter()

        # Stage 0: strip the background so the part stands alone. Both the
        # original and the cleaned image travel on: the search follows
        # whichever treatment the index it queries was built with.
        original = image
        if remove_bg:
            from backend.utils.image_utils import remove_background  # lazy: heavy dep

            image = remove_background(image)

        # Stage 1: classify the image into a category.
        classification = self._classifier.predict(image)
        category = resolve_catalog_category(classification.category)

        candidates: list[tuple[str, float]] = [(category, classification.confidence)]
        threshold_setting = get_settings().CLASSIFIER_CONFIDENCE_THRESHOLD
        classifier_uncertain = classification.confidence < threshold_setting
        if classifier_uncertain and len(classification.ranking) > 1:
            runner_label, runner_confidence = classification.ranking[1]
            runner = resolve_catalog_category(runner_label)
            if runner != category:
                logger.info(
                    "Classifier uncertain (%.2f < %.2f); also searching runner-up '%s'",
                    classification.confidence,
                    threshold_setting,
                    runner,
                )
                candidates.append((runner, runner_confidence))

        # Stage 2: search for visually similar SKUs within the candidate
        # category (or categories).
        best: _ModelStageResult | None = None
        best_margin = float("-inf")
        searched: list[str] = []
        last_error: SearchError | None = None
        for candidate_category, candidate_confidence in candidates:
            try:
                outcome = self._similarity_search.search(
                    category=candidate_category,
                    image=image,
                    top_k=top_k,
                    raw_image=original,
                )
            except SearchError as exc:
                # A fallback category without an index must not sink the
                # primary answer; if nothing at all is searchable the last
                # error surfaces below.
                last_error = exc
                continue

            searched.append(candidate_category)
            threshold = no_match_threshold(outcome.backend)
            top_score = (
                outcome.matches[0].similarity_score if outcome.matches else float("-inf")
            )
            margin = top_score - threshold
            if best is None or margin > best_margin:
                best_margin = margin
                best = _ModelStageResult(
                    category=candidate_category,
                    category_confidence=candidate_confidence,
                    outcome=outcome,
                    threshold=threshold,
                    searched_categories=[],  # filled in below with the full list
                    elapsed_ms=0.0,
                    classifier_uncertain=classifier_uncertain,
                )

        if best is None:
            raise last_error or SearchError("Similarity search produced no result.")

        best.searched_categories = searched
        best.elapsed_ms = (perf_counter() - start) * 1000
        return best
