"""Concrete `ClassifierInterface` implementation backed by EfficientNet."""

import numpy as np
from PIL.Image import Image

from backend.core.exceptions import PredictionError
from backend.core.logging import get_logger
from backend.pipeline.brain1_classifier.config import Brain1Config
from backend.pipeline.brain1_classifier.interfaces import (
    ClassificationResult,
    ClassifierInterface,
)
from backend.pipeline.brain1_classifier.labels import CATEGORY_LABELS
from backend.pipeline.brain1_classifier.model_loader import ModelLoader
from backend.pipeline.brain1_classifier.preprocess import preprocess_image

logger = get_logger(__name__)


class Classifier(ClassifierInterface):
    """EfficientNet-based part category classifier."""

    def __init__(self, config: Brain1Config | None = None) -> None:
        self._config = config or Brain1Config.from_settings()
        self._model_loader = ModelLoader(self._config)

    def load(self) -> None:
        """Load the EfficientNet model weights into memory."""
        self._model_loader.load()

    def _resolve_label(self, index: int, num_classes: int) -> str:
        """Map an output index to a class name (labels sidecar > constants > fallback)."""
        labels = self._model_loader.labels or CATEGORY_LABELS
        if 0 <= index < len(labels):
            return labels[index]
        logger.warning(
            "Predicted index %d has no label (have %d labels, model has %d classes)",
            index, len(labels), num_classes,
        )
        return f"class_{index}"

    def predict(self, image: Image) -> ClassificationResult:
        """Classify a (background-removed) part image.

        Returns:
            The predicted category label and its softmax confidence.

        Raises:
            backend.core.exceptions.ModelNotLoaded: If the model cannot be loaded.
            backend.core.exceptions.PredictionError: If inference fails.
        """
        if not self._model_loader.is_loaded:
            self.load()
        model = self._model_loader.get()

        processed = preprocess_image(image, self._config)
        # The saved model bakes in efficientnet.preprocess_input, so feed
        # raw 0-255 pixels with a batch dimension.
        batch = np.asarray(processed, dtype=np.float32)[np.newaxis, ...]

        try:
            probabilities = np.asarray(model.predict(batch, verbose=0))[0]
        except Exception as exc:  # noqa: BLE001
            raise PredictionError(f"Classifier inference failed: {exc}") from exc

        num_classes = probabilities.shape[0]
        order = np.argsort(probabilities)[::-1]
        ranking = [
            (self._resolve_label(int(i), num_classes), float(probabilities[i])) for i in order
        ]
        category, confidence = ranking[0]
        logger.info("Brain 1 predicted '%s' (confidence %.3f)", category, confidence)
        return ClassificationResult(category=category, confidence=confidence, ranking=ranking)
