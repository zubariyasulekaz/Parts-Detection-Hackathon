"""Abstract interfaces for Brain 1 (Image Classification).

Downstream code (the orchestrator, API layer, tests) should depend on
`ClassifierInterface`, not on the concrete `Classifier` implementation,
so the EfficientNet model can be swapped or mocked without touching
callers.
"""

from abc import ABC, abstractmethod

from PIL.Image import Image


class ClassificationResult:
    """Value object returned by `ClassifierInterface.predict`.

    Kept as a plain class (rather than importing the API schema) so the
    pipeline layer has no dependency on the API layer.
    """

    __slots__ = ("category", "confidence")

    def __init__(self, category: str, confidence: float) -> None:
        self.category = category
        self.confidence = confidence


class ClassifierInterface(ABC):
    """Contract for a part-image classifier."""

    @abstractmethod
    def predict(self, image: Image) -> ClassificationResult:
        """Classify a single part image.

        Args:
            image: A decoded, pre-processed PIL image.

        Returns:
            The predicted category and associated confidence score.

        Raises:
            backend.core.exceptions.ModelNotLoaded: If the model weights
                have not been loaded yet.
            backend.core.exceptions.InvalidImage: If the image cannot be
                classified.
        """
        raise NotImplementedError

    @abstractmethod
    def load(self) -> None:
        """Load model weights into memory. Must be called before `predict`."""
        raise NotImplementedError
