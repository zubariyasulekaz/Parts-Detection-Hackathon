"""Evaluation entrypoint for the Brain 1 EfficientNet classifier.

TODO: Implement evaluation against a held-out test set (accuracy,
per-category precision/recall/F1, confusion matrix export to `docs/`).

Intended to be run as a standalone script:
    python -m backend.pipeline.brain1_classifier.evaluate
"""

from backend.core.logging import get_logger
from backend.pipeline.brain1_classifier.config import Brain1Config

logger = get_logger(__name__)


def evaluate(config: Brain1Config | None = None) -> dict[str, float]:
    """Evaluate the trained classifier and return summary metrics.

    Args:
        config: Optional override of the default Brain 1 configuration.

    Returns:
        A mapping of metric name to value (e.g. `{"accuracy": 0.0}`).
    """
    config = config or Brain1Config.from_settings()
    raise NotImplementedError("Brain 1 evaluation is not implemented yet.")


if __name__ == "__main__":
    evaluate()
