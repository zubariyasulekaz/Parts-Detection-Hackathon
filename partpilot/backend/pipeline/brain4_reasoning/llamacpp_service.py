"""`ReasoningInterface` implementation backed by llama.cpp.

Runs a quantised GGUF build of the same instruction-tuned model the
`transformers` path uses, through `llama-cpp-python`. Same prompt, same
output contract - only the runtime differs.

Why a second implementation rather than a swap: `transformers` executes
full-precision weights through a general-purpose Python graph, which on a
CPU box measured ~23 seconds per explanation here. llama.cpp is built for
quantised CPU inference and reads a ~1.1 GB Q4 file instead of ~3 GB of
safetensors. The `transformers` service stays as the reference path (and
the one that needs no extra dependency), selected by `LLM_BACKEND`.

Like every Brain 4 implementation this is optional: the orchestrator
catches a `ReasoningError` and returns the Brain 1-3 answer unchanged.
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


class LlamaCppService(ReasoningInterface):
    """llama.cpp-backed reasoning/explanation service."""

    def __init__(
        self,
        repo_id: str | None = None,
        filename: str | None = None,
        max_new_tokens: int | None = None,
        prompt_builder: PromptBuilder | None = None,
    ) -> None:
        settings = get_settings()
        self._repo_id = repo_id or settings.LLM_GGUF_REPO
        self._filename = filename or settings.LLM_GGUF_FILE
        self._max_new_tokens = max_new_tokens or settings.LLM_MAX_NEW_TOKENS
        self._context_tokens = settings.LLM_CONTEXT_TOKENS
        self._threads = settings.LLM_THREADS or None
        self._hf_token = settings.HF_TOKEN
        self._prompt_builder = prompt_builder or PromptBuilder()
        self._llm: Any | None = None
        self._load_error: str | None = None

    def _load(self) -> Any:
        """Load (and cache) the GGUF model.

        A failed load is remembered rather than retried: fetching weights can
        stall for minutes behind HTTP retries, and this instance is a
        process-wide singleton, so retrying per request would stall every
        prediction. Restart the process to try again.
        """
        if self._llm is not None:
            return self._llm
        if self._load_error is not None:
            raise ReasoningError(self._load_error)

        try:
            from llama_cpp import Llama  # noqa: PLC0415
        except ImportError as exc:  # pragma: no cover - env-dependent
            self._load_error = (
                "llama-cpp-python is not installed; cannot load the Brain 4 GGUF model. "
                "Install it, or set LLM_BACKEND=transformers."
            )
            raise ReasoningError(self._load_error) from exc

        logger.info("Loading Brain 4 GGUF: %s/%s", self._repo_id, self._filename)
        try:
            kwargs: dict[str, Any] = {
                "repo_id": self._repo_id,
                "filename": self._filename,
                "n_ctx": self._context_tokens,
                "verbose": False,
            }
            if self._threads is not None:
                kwargs["n_threads"] = self._threads
            if self._hf_token:
                kwargs["additional_files"] = []
                kwargs["token"] = self._hf_token
            self._llm = Llama.from_pretrained(**kwargs)
        except Exception as exc:  # noqa: BLE001
            self._load_error = (
                f"Could not load the Brain 4 GGUF model ({self._repo_id}/{self._filename}): {exc}. "
                "Explanations are disabled until the backend is restarted."
            )
            logger.warning(self._load_error)
            raise ReasoningError(self._load_error) from exc
        return self._llm

    def warm(self) -> None:
        """Load the model now rather than inside the first request.

        Optional, and never fatal: `backend.core.startup` calls this when the
        setting allows, and a failure here degrades exactly as it would have
        inside the request - to no explanation.
        """
        self._load()

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
        llm = self._load()
        user_prompt = self._prompt_builder.build_explanation_prompt(
            prediction, product, recommendation
        )

        try:
            # temperature=0 for the same reason the transformers path uses
            # greedy decoding: a demo should say the same thing twice.
            output = llm.create_chat_completion(
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": user_prompt},
                ],
                max_tokens=self._max_new_tokens,
                temperature=0.0,
            )
        except Exception as exc:  # noqa: BLE001
            raise ReasoningError(f"Brain 4 GGUF generation failed: {exc}") from exc

        return str(output["choices"][0]["message"]["content"]).strip()
