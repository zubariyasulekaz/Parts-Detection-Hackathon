"""Concrete `ReasoningInterface` implementation (future module).

TODO (future): Implement using a Hugging Face `transformers` pipeline
or Inference Endpoint, authenticated via `Settings.HF_TOKEN`. Not
implemented in this skeleton per project scope.
"""

from backend.core.logging import get_logger
from backend.pipeline.brain4_reasoning.interfaces import ReasoningInterface
from backend.pipeline.brain4_reasoning.prompt_builder import PromptBuilder
from backend.schemas.catalog import Product
from backend.schemas.prediction import PredictionResponse
from backend.schemas.recommendation import Recommendation

logger = get_logger(__name__)


class LLMService(ReasoningInterface):
    """Hugging Face-backed reasoning/explanation service."""

    def __init__(self, prompt_builder: PromptBuilder | None = None) -> None:
        self._prompt_builder = prompt_builder or PromptBuilder()

    def explain(
        self,
        prediction: PredictionResponse,
        product: Product | None,
        recommendation: Recommendation | None,
    ) -> str:
        """Generate a natural-language explanation of the pipeline result.

        TODO (future): Build the prompt via `self._prompt_builder`, call
        the Hugging Face model/endpoint, and return the generated text.
        """
        raise NotImplementedError("Brain 4 LLMService.explain is not implemented yet.")
