"""Concrete `EmbeddingGeneratorInterface` implementation backed by OpenCLIP."""

import numpy as np
from PIL.Image import Image

from backend.core.exceptions import EmbeddingError
from backend.core.logging import get_logger
from backend.pipeline.brain2_similarity.clip_model import CLIPModel
from backend.pipeline.brain2_similarity.interfaces import EmbeddingGeneratorInterface

logger = get_logger(__name__)


class EmbeddingGenerator(EmbeddingGeneratorInterface):
    """Generates L2-normalized OpenCLIP image embeddings for similarity search."""

    def __init__(self, clip_model: CLIPModel | None = None) -> None:
        self._clip_model = clip_model or CLIPModel()

    def generate(self, image: Image) -> np.ndarray:
        """Generate an L2-normalized OpenCLIP embedding for the given image.

        Returns:
            A 1-D ``float32`` ``numpy.ndarray`` of unit length.

        Raises:
            backend.core.exceptions.EmbeddingError: If encoding fails.
        """
        try:
            import torch  # noqa: PLC0415
        except ImportError as exc:  # pragma: no cover - env-dependent
            raise EmbeddingError("torch is not installed; cannot generate embeddings.") from exc

        if not self._clip_model.is_loaded:
            self._clip_model.load()
        model, preprocess = self._clip_model.get()

        try:
            tensor = preprocess(image.convert("RGB")).unsqueeze(0).to(self._clip_model.device)
            with torch.no_grad():
                embedding = model.encode_image(tensor)
            embedding = embedding / embedding.norm(dim=-1, keepdim=True)
            return embedding.squeeze(0).cpu().numpy().astype(np.float32)
        except Exception as exc:  # noqa: BLE001
            raise EmbeddingError(f"Failed to generate embedding: {exc}") from exc
