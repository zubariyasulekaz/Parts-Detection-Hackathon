"""Abstract interfaces for Brain 2 (Similarity Search).

Downstream code should depend on `SimilaritySearchInterface`, not the
concrete `SimilaritySearchService` implementation.
"""

from abc import ABC, abstractmethod

import numpy as np
from PIL.Image import Image


class SimilarityMatch:
    """A single top-K match returned by a similarity search."""

    __slots__ = ("sku", "similarity_score")

    def __init__(self, sku: str, similarity_score: float) -> None:
        self.sku = sku
        self.similarity_score = similarity_score


class EmbeddingGeneratorInterface(ABC):
    """Contract for turning an image into a fixed-size embedding vector."""

    @abstractmethod
    def generate(self, image: Image) -> np.ndarray:
        """Generate an OpenCLIP embedding for the given image.

        Args:
            image: A decoded, pre-processed PIL image.

        Returns:
            A 1-D `numpy.ndarray` embedding vector.

        Raises:
            backend.core.exceptions.EmbeddingError: If embedding generation fails.
        """
        raise NotImplementedError


class SimilaritySearchInterface(ABC):
    """Contract for category-scoped visual similarity search."""

    @abstractmethod
    def search(
        self,
        category: str,
        image: Image,
        top_k: int = 10,
    ) -> list[SimilarityMatch]:
        """Find the top-K most visually similar SKUs within a category.

        Args:
            category: Predicted category from Brain 1, used to select
                which FAISS index to query.
            image: The source part image.
            top_k: Number of matches to return.

        Returns:
            Matches ordered by descending similarity score.

        Raises:
            backend.core.exceptions.SearchError: If the search fails
                (e.g. missing index for the category).
        """
        raise NotImplementedError
