"""Model loading utilities for the Brain 1 classifier.

TODO: Implement actual TensorFlow/Keras (EfficientNet) checkpoint
loading, including any GPU/CPU device placement logic.
"""

from typing import Any

from backend.core.exceptions import ModelNotLoaded
from backend.core.logging import get_logger
from backend.pipeline.brain1_classifier.config import Brain1Config

logger = get_logger(__name__)


class ModelLoader:
    """Loads and caches the EfficientNet classifier model."""

    def __init__(self, config: Brain1Config) -> None:
        self._config = config
        self._model: Any | None = None

    @property
    def is_loaded(self) -> bool:
        """Whether the model has been loaded into memory."""
        return self._model is not None

    def load(self) -> Any:
        """Load the model from `self._config.model_path`.

        Returns:
            The loaded model object (framework-specific).

        TODO: Implement with `tensorflow.keras.models.load_model` (or
        equivalent) pointed at `self._config.model_path`.
        """
        raise NotImplementedError("EfficientNet model loading is not implemented yet.")

    def get(self) -> Any:
        """Return the cached model, loading it on first access.

        Raises:
            backend.core.exceptions.ModelNotLoaded: If loading has not
                succeeded yet.
        """
        if self._model is None:
            raise ModelNotLoaded("Brain 1 classifier model has not been loaded.")
        return self._model
