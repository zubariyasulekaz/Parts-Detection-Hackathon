"""Abstract interfaces for Brain 4 (Reasoning).

Downstream code should depend on `ReasoningInterface`, not the concrete
`LLMService` (Qwen, via Hugging Face `transformers`) implementation.
"""

from abc import ABC, abstractmethod

from backend.schemas.catalog import Product
from backend.schemas.prediction import PredictionResponse
from backend.schemas.recommendation import Recommendation


class ReasoningInterface(ABC):
    """Contract for LLM-based explanation generation."""

    @abstractmethod
    def explain(
        self,
        prediction: PredictionResponse,
        product: Product | None,
        recommendation: Recommendation | None,
    ) -> str:
        """Generate a natural-language explanation of the pipeline result.

        Args:
            prediction: Output of Brain 1 + Brain 2.
            product: Output of Brain 3 (`CatalogInterface.get_product`),
                if a confident SKU match was found.
            recommendation: Output of Brain 3
                (`RecommendationInterface.recommend`), if available.

        Returns:
            A human-readable explanation, plus clarifying questions when
            the match is ambiguous.

        Raises:
            backend.core.exceptions.ReasoningError: If the model cannot
                be loaded or generation fails.
        """
        raise NotImplementedError
