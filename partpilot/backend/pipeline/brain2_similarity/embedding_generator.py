"""Concrete `EmbeddingGeneratorInterface` implementation.

Which model produces the vector is decided by ``EMBEDDING_BACKEND`` (see
``embedding_backends.py``) - OpenCLIP, SigLIP, DINOv2, or a combination.
Whatever the backend, the output is a single L2-normalized vector, so the FAISS
layer never has to care which model made it.

Changing the backend invalidates existing indexes: vectors from different models
are not comparable, so rebuild them after switching.
"""

import numpy as np
from PIL.Image import Image

from backend.core.exceptions import EmbeddingError
from backend.core.logging import get_logger
from backend.pipeline.brain2_similarity.embedding_backends import (
    EmbeddingBackend,
    build_backend,
)
from backend.pipeline.brain2_similarity.interfaces import EmbeddingGeneratorInterface

logger = get_logger(__name__)


class EmbeddingGenerator(EmbeddingGeneratorInterface):
    """Generates L2-normalized image embeddings for similarity search."""

    def __init__(
        self,
        backend: EmbeddingBackend | None = None,
        backend_spec: str | None = None,
    ) -> None:
        """
        Args:
            backend: A ready-made backend (mainly for tests).
            backend_spec: Override the configured backend, e.g. ``"dinov2+siglip"``.
        """
        self._backend = backend or build_backend(backend_spec)

    @property
    def backend_name(self) -> str:
        """Which model(s) are producing the vectors."""
        return self._backend.name

    def generate(self, image: Image) -> np.ndarray:
        """Generate an L2-normalized embedding for the given image.

        Returns:
            A 1-D ``float32`` ``numpy.ndarray`` of unit length.

        Raises:
            backend.core.exceptions.EmbeddingError: If encoding fails.
        """
        try:
            return self._backend.encode(image)
        except EmbeddingError:
            raise
        except Exception as exc:  # noqa: BLE001
            raise EmbeddingError(f"Failed to generate embedding: {exc}") from exc
