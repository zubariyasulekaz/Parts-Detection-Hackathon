"""Brain 1-specific configuration.

Separate from the global `backend.config.settings.Settings` so classifier
hyperparameters can evolve independently of application-wide config.
"""

from dataclasses import dataclass

from backend.config.settings import get_settings


@dataclass(frozen=True)
class Brain1Config:
    """Configuration for the EfficientNet classifier.

    TODO: Extend with the final architecture variant, checkpoint
    filename convention, normalization stats, etc. once training is
    finalized.
    """

    model_path: str
    input_size: int
    confidence_threshold: float
    pad_to_square: bool = False

    @classmethod
    def from_settings(cls) -> "Brain1Config":
        """Build a `Brain1Config` from the global application settings."""
        settings = get_settings()
        return cls(
            model_path=settings.MODEL_PATH,
            input_size=settings.CLASSIFIER_INPUT_SIZE,
            confidence_threshold=settings.CLASSIFIER_CONFIDENCE_THRESHOLD,
            pad_to_square=settings.CLASSIFIER_PAD_TO_SQUARE,
        )
