"""Concrete `EmbeddingGeneratorInterface` implementation backed by OpenCLIP.

TODO: Implement actual embedding generation via the wrapped `CLIPModel`.
"""

import numpy as np
from PIL.Image import Image

from backend.core.logging import get_logger
from backend.pipeline.brain2_similarity.clip_model import CLIPModel
from backend.pipeline.brain2_similarity.interfaces import EmbeddingGeneratorInterface

logger = get_logger(__name__)


class EmbeddingGenerator(EmbeddingGeneratorInterface):
    """Generates OpenCLIP image embeddings for similarity search."""

    def __init__(self, clip_model: CLIPModel | None = None) -> None:
        self._clip_model = clip_model or CLIPModel()

    def generate(self, image: Image) -> np.ndarray:
        """Generate an OpenCLIP embedding for the given image.

        TODO:
            1. Apply the OpenCLIP preprocessing transform.
            2. Run the image encoder forward pass.
            3. L2-normalize the resulting embedding.
        """
        raise NotImplementedError("OpenCLIP embedding generation is not implemented yet.")
