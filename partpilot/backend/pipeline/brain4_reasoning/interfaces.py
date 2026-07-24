"""Abstract interfaces for Brain 4 (Reasoning).

This module intentionally contains ONLY interfaces/value objects. No
implementation exists yet — Brain 4 is a future module that will wrap a
Hugging Face LLM to generate natural-language explanations of the
Brain 1-3 results.
"""

from abc import ABC, abstractmethod

from backend.schemas.catalog import Product
from backend.schemas.prediction import PredictionResponse
from backend.schemas.recommendation import Recommendation


class ReasoningInterface(ABC):
    """Contract for LLM-based explanation generation.

    TODO (future): Define the concrete implementation in `llm_service.py`
    once a Hugging Face model/endpoint is selected.
    """

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
            A human-readable explanation string.

        Raises:
            NotImplementedError: Always, until Brain 4 is implemented.
        """
        raise NotImplementedError
