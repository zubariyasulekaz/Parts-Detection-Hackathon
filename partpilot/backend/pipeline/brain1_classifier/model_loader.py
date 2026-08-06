"""Model loading utilities for the Brain 1 classifier.

Loads a Keras EfficientNet checkpoint (``.keras``) plus an optional
``labels.json`` sidecar listing class names in the model's output order
(as produced by ``image_dataset_from_directory().class_names`` during
training). ``tensorflow`` is imported lazily so this module imports fine
where TF is not installed.
"""

import json
import os
from pathlib import Path
from typing import Any

from backend.core.exceptions import ModelNotLoaded
from backend.core.logging import get_logger
from backend.pipeline.brain1_classifier.config import Brain1Config

logger = get_logger(__name__)

#: Default checkpoint filename produced by the training notebook.
_DEFAULT_CHECKPOINT = "brain1_classifier.keras"
#: Optional sidecar listing class names in output-layer order.
_LABELS_SIDECAR = "labels.json"


class ModelLoader:
    """Loads and caches the EfficientNet classifier model + its labels."""

    def __init__(self, config: Brain1Config) -> None:
        self._config = config
        self._model: Any | None = None
        self._labels: list[str] | None = None

    @property
    def is_loaded(self) -> bool:
        """Whether the model has been loaded into memory."""
        return self._model is not None

    @property
    def labels(self) -> list[str] | None:
        """Class names in output order, if a ``labels.json`` sidecar was found."""
        return self._labels

    def _resolve_checkpoint(self) -> Path:
        """Resolve the configured path to a concrete ``.keras`` file."""
        path = Path(self._config.model_path)
        if path.is_dir():
            candidate = path / _DEFAULT_CHECKPOINT
            if candidate.exists():
                return candidate
            keras_files = sorted(path.glob("*.keras"))
            if keras_files:
                return keras_files[0]
            raise ModelNotLoaded(f"No .keras checkpoint found in {path}")
        if not path.exists():
            raise ModelNotLoaded(f"Classifier checkpoint not found: {path}")
        return path

    def load(self) -> Any:
        """Load the model (and labels sidecar) from `self._config.model_path`."""
        # TensorFlow prints oneDNN and CPU-instruction banners to stderr the first
        # time it is imported, which buries the server's own startup log. These are
        # informational only, and must be set before the import to take effect.
        os.environ.setdefault("TF_CPP_MIN_LOG_LEVEL", "2")
        os.environ.setdefault("TF_ENABLE_ONEDNN_OPTS", "0")
        try:
            import tensorflow as tf  # noqa: PLC0415
        except ImportError as exc:  # pragma: no cover - env-dependent
            raise ModelNotLoaded(
                "tensorflow is not installed; cannot load the Brain 1 classifier."
            ) from exc

        checkpoint = self._resolve_checkpoint()
        self._model = tf.keras.models.load_model(checkpoint)

        labels_path = checkpoint.parent / _LABELS_SIDECAR
        if labels_path.exists():
            self._labels = json.loads(labels_path.read_text(encoding="utf-8"))
            logger.info("Loaded %d classifier labels from %s", len(self._labels), labels_path)
        else:
            logger.warning(
                "No %s beside %s; falling back to constants.CATEGORY_LABELS ordering.",
                _LABELS_SIDECAR,
                checkpoint.name,
            )

        logger.info("Loaded Brain 1 classifier from %s", checkpoint)
        return self._model

    def get(self) -> Any:
        """Return the cached model, loading it on first access.

        Raises:
            backend.core.exceptions.ModelNotLoaded: If loading has not
                succeeded yet.
        """
        if self._model is None:
            raise ModelNotLoaded("Brain 1 classifier model has not been loaded.")
        return self._model
