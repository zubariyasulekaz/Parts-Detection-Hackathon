"""Concrete `ClassifierInterface` implementation backed by EfficientNet.

TODO: Implement actual inference. This class currently exists only to
satisfy the interface contract and wire up dependency injection.
"""

from PIL.Image import Image

from backend.core.logging import get_logger
from backend.pipeline.brain1_classifier.config import Brain1Config
from backend.pipeline.brain1_classifier.interfaces import (
    ClassificationResult,
    ClassifierInterface,
)
from backend.pipeline.brain1_classifier.model_loader import ModelLoader

logger = get_logger(__name__)


class Classifier(ClassifierInterface):
    """EfficientNet-based part category classifier."""

    def __init__(self, config: Brain1Config | None = None) -> None:
        self._config = config or Brain1Config.from_settings()
        self._model_loader = ModelLoader(self._config)

    def load(self) -> None:
        """Load the EfficientNet model weights.

        TODO: Delegate to `self._model_loader.load()` once implemented.
        """
        raise NotImplementedError("Brain 1 Classifier.load is not implemented yet.")

    def predict(self, image: Image) -> ClassificationResult:
        """Classify a pre-processed part image.

        TODO:
            1. Run `backend.pipeline.brain1_classifier.preprocess.preprocess_image`.
            2. Run inference via `self._model_loader.get()`.
            3. Decode the argmax index via
               `backend.pipeline.brain1_classifier.labels.decode_label`.
        """
        raise NotImplementedError("Brain 1 Classifier.predict is not implemented yet.")
