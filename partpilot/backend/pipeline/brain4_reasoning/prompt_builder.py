"""Prompt construction for Brain 4 (Reasoning).

TODO (future): Implement prompt templates once the target Hugging Face
model is chosen. Left as a stub so `llm_service.py` has something to
import against without coupling to a specific prompt format yet.
"""

from backend.schemas.catalog import Product
from backend.schemas.prediction import PredictionResponse
from backend.schemas.recommendation import Recommendation


class PromptBuilder:
    """Builds LLM prompts from pipeline results.

    TODO (future): Implement `build_explanation_prompt`.
    """

    def build_explanation_prompt(
        self,
        prediction: PredictionResponse,
        product: Product | None,
        recommendation: Recommendation | None,
    ) -> str:
        """Construct the prompt sent to the Brain 4 LLM.

        Raises:
            NotImplementedError: Always, until Brain 4 is implemented.
        """
        raise NotImplementedError("Brain 4 prompt building is not implemented yet.")
