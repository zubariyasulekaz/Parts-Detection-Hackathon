"""Thin wrapper around a single category's FAISS index file.

Uses ``faiss.IndexFlatIP`` (inner product). Because both the stored product
vectors and the query vectors are L2-normalized, inner product equals cosine
similarity, so scores are in ``[-1, 1]`` (higher = more similar).

Each index has a JSON sidecar (``<name>.ids.json``) mapping the FAISS row
position to the catalog SKU, since ``IndexFlatIP`` stores only vectors.

``faiss`` is imported lazily inside methods so the rest of the backend (and
its tests) can import this module even where ``faiss-cpu`` is not installed.
"""

import json
from pathlib import Path
from typing import Any

import numpy as np

from backend.core.exceptions import SearchError
from backend.core.logging import get_logger

logger = get_logger(__name__)


def _import_faiss() -> Any:
    try:
        import faiss  # noqa: PLC0415
    except ImportError as exc:  # pragma: no cover - env-dependent
        raise SearchError(
            "faiss is not installed. Install `faiss-cpu` to build or query indexes."
        ) from exc
    return faiss


def _as_query_matrix(vector: np.ndarray) -> np.ndarray:
    """Return a normalized ``(1, dim)`` float32 matrix for a 1-D vector."""
    matrix = np.asarray(vector, dtype=np.float32).reshape(1, -1)
    norms = np.linalg.norm(matrix, axis=1, keepdims=True)
    norms[norms == 0] = 1.0
    return matrix / norms


class FaissIndex:
    """Wraps a single category's FAISS index plus its SKU id mapping."""

    def __init__(self, index_path: Path) -> None:
        self._index_path = Path(index_path)
        self._ids_path = self._index_path.parent / f"{self._index_path.stem}.ids.json"
        # Records which embedding model produced these vectors. A query
        # embedded by a different model is not comparable to them, so the
        # search side reads this rather than assuming the configured default.
        self._meta_path = self._index_path.parent / f"{self._index_path.stem}.meta.json"
        self._index: Any | None = None
        # Maps FAISS internal vector position -> catalog SKU.
        self._id_to_sku: list[str] = []
        self._backend: str | None = None

    @property
    def backend(self) -> str | None:
        """Embedding backend that built this index, if recorded."""
        return self._backend

    @property
    def is_loaded(self) -> bool:
        """Whether the FAISS index has been loaded into memory."""
        return self._index is not None

    @property
    def size(self) -> int:
        """Number of vectors currently in the index."""
        return len(self._id_to_sku)

    def load(self) -> None:
        """Load the FAISS index and its SKU id map from disk."""
        faiss = _import_faiss()
        if not self._index_path.exists():
            raise SearchError(f"FAISS index file not found: {self._index_path}")
        if not self._ids_path.exists():
            raise SearchError(f"FAISS id-map sidecar not found: {self._ids_path}")

        self._index = faiss.read_index(str(self._index_path))
        self._id_to_sku = json.loads(self._ids_path.read_text(encoding="utf-8"))
        if self._meta_path.exists():
            self._backend = json.loads(self._meta_path.read_text(encoding="utf-8")).get("backend")
        logger.info(
            "Loaded FAISS index %s (%d vectors%s)",
            self._index_path.name,
            self.size,
            f", backend={self._backend}" if self._backend else "",
        )

    def search(self, query_vector: np.ndarray, top_k: int) -> list[tuple[str, float]]:
        """Search the index for the top-K nearest neighbors.

        Returns:
            A list of ``(sku, similarity_score)`` tuples ordered by
            descending similarity. Cosine scores are in ``[-1, 1]``.

        Raises:
            backend.core.exceptions.SearchError: If the index is not loaded.
        """
        if self._index is None:
            raise SearchError(f"FAISS index at {self._index_path} has not been loaded.")
        if self.size == 0 or top_k <= 0:
            return []

        query = _as_query_matrix(query_vector)
        scores, indices = self._index.search(query, min(top_k, self.size))

        results: list[tuple[str, float]] = []
        for idx, score in zip(indices[0], scores[0]):
            if idx == -1:  # padding when top_k > ntotal
                continue
            results.append((self._id_to_sku[idx], float(score)))
        return results

    def add(self, sku: str, vector: np.ndarray) -> None:
        """Add a single (already product-level) embedding vector to the index.

        The index is created on the first add, sized to the vector's dimension.
        """
        faiss = _import_faiss()
        matrix = _as_query_matrix(vector)
        if self._index is None:
            self._index = faiss.IndexFlatIP(matrix.shape[1])
            self._id_to_sku = []
        self._index.add(matrix)
        self._id_to_sku.append(sku)

    def save(self, backend: str | None = None) -> None:
        """Persist the index, its id map, and which backend built it.

        Args:
            backend: Name of the embedding backend used to build these
                vectors. Stored alongside the index so the query side can
                embed with the same model.
        """
        faiss = _import_faiss()
        if self._index is None:
            raise SearchError("Cannot save an empty FAISS index (nothing added).")
        self._index_path.parent.mkdir(parents=True, exist_ok=True)
        faiss.write_index(self._index, str(self._index_path))
        self._ids_path.write_text(json.dumps(self._id_to_sku), encoding="utf-8")
        if backend:
            self._backend = backend
            self._meta_path.write_text(json.dumps({"backend": backend}), encoding="utf-8")
        logger.info(
            "Saved FAISS index %s (%d vectors%s)",
            self._index_path.name,
            self.size,
            f", backend={backend}" if backend else "",
        )
