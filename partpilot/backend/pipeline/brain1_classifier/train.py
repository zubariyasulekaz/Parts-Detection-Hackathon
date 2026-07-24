"""Training entrypoint for the Brain 1 EfficientNet classifier.

TODO: Implement the full training loop (dataset loading from
`datasets/`, augmentation, fine-tuning EfficientNet, checkpointing to
`backend/models/classifier/`, TensorBoard/experiment logging, etc.).

Intended to be run as a standalone script:
    python -m backend.pipeline.brain1_classifier.train
"""

from backend.core.logging import get_logger
from backend.pipeline.brain1_classifier.config import Brain1Config

logger = get_logger(__name__)


def train(config: Brain1Config | None = None) -> None:
    """Train (or fine-tune) the EfficientNet classifier.

    Args:
        config: Optional override of the default Brain 1 configuration.
    """
    config = config or Brain1Config.from_settings()
    raise NotImplementedError("Brain 1 training loop is not implemented yet.")


if __name__ == "__main__":
    train()
