"""Concrete `EmbeddingGeneratorInterface` implementation.

Which model produces the vector is decided by ``EMBEDDING_BACKEND`` (see
``embedding_backends.py``) - OpenCLIP, SigLIP, DINOv2, or a combination.
Whatever the backend, the output is a single L2-normalized vector, so the FAISS
layer never has to care which model made it.

Changing the backend invalidates existing indexes: vectors from different models
are not comparable, so rebuild them after switching.
"""

import numpy as np
from PIL import Image as PILImage
from PIL.Image import Image

from backend.config.settings import get_settings
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

    def generate(self, image: Image, tta: bool | None = None) -> np.ndarray:
        """Generate an L2-normalized embedding for the given image.

        With ``tta`` (default from ``Settings.EMBEDDING_TTA``), the image and
        its mirror are both encoded and their embeddings averaged, then
        re-normalized. A part photographed from the "wrong" side then still
        lands near its catalog shots. Index vectors and query vectors must
        agree on this setting — it is applied in both places by living here.

        Returns:
            A 1-D ``float32`` ``numpy.ndarray`` of unit length.

        Raises:
            backend.core.exceptions.EmbeddingError: If encoding fails.
        """
        use_tta = get_settings().EMBEDDING_TTA if tta is None else tta
        try:
            vectors = [self._backend.encode(image)]
            if use_tta:
                vectors.append(self._backend.encode(image.transpose(PILImage.FLIP_LEFT_RIGHT)))
            if len(vectors) == 1:
                return vectors[0]
            mean = np.mean(np.stack(vectors), axis=0)
            norm = np.linalg.norm(mean)
            return (mean / norm if norm else mean).astype(np.float32)
        except EmbeddingError:
            raise
        except Exception as exc:  # noqa: BLE001
            raise EmbeddingError(f"Failed to generate embedding: {exc}") from exc
