"""Concrete `ReasoningInterface` implementation.

Uses a small instruction-tuned Qwen model (Hugging Face `transformers`)
to turn the Brain 1-3 outputs into a short natural-language explanation,
plus a few clarifying questions when the match is ambiguous. The model
is loaded lazily on first use and cached process-wide (see
`backend.api.dependencies.get_reasoning_service`), since it's the
heaviest of the four brains to spin up.
"""

from typing import Any

from backend.config.settings import get_settings
from backend.core.exceptions import ReasoningError
from backend.core.logging import get_logger
from backend.pipeline.brain4_reasoning.interfaces import ReasoningInterface
from backend.pipeline.brain4_reasoning.prompt_builder import SYSTEM_PROMPT, PromptBuilder
from backend.schemas.catalog import Product
from backend.schemas.prediction import PredictionResponse
from backend.schemas.recommendation import Recommendation

logger = get_logger(__name__)


class LLMService(ReasoningInterface):
    """Qwen-backed (Hugging Face `transformers`) reasoning/explanation service."""

    def __init__(
        self,
        model_name: str | None = None,
        hf_token: str | None = None,
        max_new_tokens: int | None = None,
        prompt_builder: PromptBuilder | None = None,
    ) -> None:
        settings = get_settings()
        self._model_name = model_name or settings.LLM_MODEL_NAME
        self._hf_token = hf_token or settings.HF_TOKEN
        self._max_new_tokens = max_new_tokens or settings.LLM_MAX_NEW_TOKENS
        self._prompt_builder = prompt_builder or PromptBuilder()
        self._pipeline: Any | None = None

    def _load(self) -> Any:
        """Load (and cache) the Qwen text-generation pipeline."""
        if self._pipeline is not None:
            return self._pipeline
        try:
            from transformers import pipeline  # noqa: PLC0415
        except ImportError as exc:  # pragma: no cover - env-dependent
            raise ReasoningError(
                "transformers/torch are not installed; cannot load the Brain 4 LLM."
            ) from exc

        logger.info("Loading Brain 4 LLM: %s", self._model_name)
        self._pipeline = pipeline(
            task="text-generation",
            model=self._model_name,
            token=self._hf_token,
            torch_dtype="auto",
            device_map="auto",
        )
        return self._pipeline

    def explain(
        self,
        prediction: PredictionResponse,
        product: Product | None,
        recommendation: Recommendation | None,
    ) -> str:
        """Generate a short explanation, with clarifying questions when useful.

        Raises:
            backend.core.exceptions.ReasoningError: If the model cannot be
                loaded or generation fails.
        """
        pipe = self._load()
        user_prompt = self._prompt_builder.build_explanation_prompt(
            prediction, product, recommendation
        )
        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ]

        try:
            output = pipe(messages, max_new_tokens=self._max_new_tokens, do_sample=False)
        except Exception as exc:  # noqa: BLE001
            raise ReasoningError(f"Brain 4 LLM generation failed: {exc}") from exc

        generated = output[0]["generated_text"]
        # With chat-style input, `generated_text` is the full message list;
        # the model's reply is always the last entry.
        reply = generated[-1]["content"] if isinstance(generated, list) else str(generated)
        return reply.strip()
