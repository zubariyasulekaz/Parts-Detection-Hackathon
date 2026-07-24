"""Thin wrapper around a single FAISS index file.

TODO: Implement actual FAISS index load/save/search (e.g. using
`faiss.IndexFlatIP` or `faiss.IndexIVFFlat` depending on catalog scale).
"""

from pathlib import Path
from typing import Any

import numpy as np

from backend.core.exceptions import SearchError
from backend.core.logging import get_logger

logger = get_logger(__name__)


class FaissIndex:
    """Wraps a single category's FAISS index plus its SKU id mapping."""

    def __init__(self, index_path: Path) -> None:
        self._index_path = index_path
        self._index: Any | None = None
        # Maps FAISS internal vector position -> catalog SKU.
        self._id_to_sku: list[str] = []

    @property
    def is_loaded(self) -> bool:
        """Whether the FAISS index has been loaded into memory."""
        return self._index is not None

    def load(self) -> None:
        """Load the FAISS index (and its SKU id map) from disk.

        TODO: Implement via `faiss.read_index(str(self._index_path))`
        plus loading the accompanying id-map sidecar file.
        """
        raise NotImplementedError("FAISS index loading is not implemented yet.")

    def search(self, query_vector: np.ndarray, top_k: int) -> list[tuple[str, float]]:
        """Search the index for the top-K nearest neighbors.

        Args:
            query_vector: 1-D embedding vector to search with.
            top_k: Number of neighbors to return.

        Returns:
            A list of `(sku, similarity_score)` tuples, ordered by
            descending similarity.

        Raises:
            backend.core.exceptions.SearchError: If the index has not
                been loaded or the search otherwise fails.
        """
        if self._index is None:
            raise SearchError(f"FAISS index at {self._index_path} has not been loaded.")
        raise NotImplementedError("FAISS search is not implemented yet.")

    def add(self, sku: str, vector: np.ndarray) -> None:
        """Add a single embedding vector to the index.

        TODO: Implement incremental index updates for newly onboarded
        catalog products (100k+ scale likely needs batched adds instead).
        """
        raise NotImplementedError("FAISS index add is not implemented yet.")

    def save(self) -> None:
        """Persist the index (and id map) back to `self._index_path`.

        TODO: Implement via `faiss.write_index`.
        """
        raise NotImplementedError("FAISS index saving is not implemented yet.")
