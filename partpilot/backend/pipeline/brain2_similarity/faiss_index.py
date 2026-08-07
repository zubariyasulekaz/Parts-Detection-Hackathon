"""Thin wrapper around a single category's FAISS index file.

Uses ``faiss.IndexFlatIP`` (inner product). Because both the stored product
vectors and the query vectors are L2-normalized, inner product equals cosine
similarity, so scores are in ``[-1, 1]`` (higher = more similar).

Each index has a JSON sidecar (``<name>.ids.json``) mapping the FAISS row
position to the catalog SKU, since ``IndexFlatIP`` stores only vectors. A SKU
may own several rows — one per catalog image — and a search scores each SKU
against the L2-normalized *centroid* of its image vectors, computed at load
time. Measured on the catalog (scripts/analyze_index_vectors.py), centroid
scoring ranks the correct SKU first in 79% of leave-one-out queries vs 72%
for max-over-images: with 2-7 photos per product, the max is one lucky
angle away from promoting the wrong SKU, while the centroid averages that
noise out. Storing per-image vectors anyway (rather than a prebuilt
centroid) keeps every photo inspectable, lets the evaluation exclude a
held-out image exactly, and leaves room to re-aggregate without re-embedding.

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
        self._remove_bg: bool | None = None
        # Per-SKU centroids, derived from the rows; rebuilt lazily after adds.
        self._centroid_skus: list[str] = []
        self._centroids: np.ndarray = np.empty((0, 0), dtype=np.float32)
        self._centroids_dirty = False

    @property
    def backend(self) -> str | None:
        """Embedding backend that built this index, if recorded."""
        return self._backend

    @property
    def remove_bg(self) -> bool | None:
        """Whether the indexed vectors were built from background-removed
        images, if recorded. The query image must be preprocessed the same
        way or scores silently degrade."""
        return self._remove_bg

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
            meta = json.loads(self._meta_path.read_text(encoding="utf-8"))
            self._backend = meta.get("backend")
            self._remove_bg = meta.get("remove_bg")
        self._build_centroids()
        logger.info(
            "Loaded FAISS index %s (%d vectors%s)",
            self._index_path.name,
            self.size,
            f", backend={self._backend}" if self._backend else "",
        )

    def _build_centroids(self) -> None:
        """Precompute one L2-normalized centroid per SKU from the stored rows.

        Category indexes are small (a handful of SKUs, a few photos each),
        so the centroids live as a dense matrix scored with one matmul per
        query. At larger scale the same centroids would go into a second
        ``IndexFlatIP`` instead — the search contract wouldn't change.
        """
        self._centroids_dirty = False
        if self._index is None or not self._id_to_sku:
            self._centroid_skus = []
            self._centroids = np.empty((0, 0), dtype=np.float32)
            return
        vectors = self._index.reconstruct_n(0, self._index.ntotal)
        rows_by_sku: dict[str, list[int]] = {}
        for row, sku in enumerate(self._id_to_sku):
            rows_by_sku.setdefault(sku, []).append(row)
        centroids = []
        for sku, rows in rows_by_sku.items():
            mean = vectors[rows].mean(axis=0)
            norm = np.linalg.norm(mean)
            centroids.append(mean / norm if norm else mean)
        self._centroid_skus = list(rows_by_sku)
        self._centroids = np.stack(centroids).astype(np.float32)

    def search(self, query_vector: np.ndarray, top_k: int) -> list[tuple[str, float]]:
        """Return the top-K SKUs by cosine similarity to their centroids.

        Returns:
            A list of ``(sku, similarity_score)`` tuples ordered by
            descending similarity, one entry per SKU. Cosine scores are in
            ``[-1, 1]``.

        Raises:
            backend.core.exceptions.SearchError: If the index is not loaded.
        """
        if self._index is None:
            raise SearchError(f"FAISS index at {self._index_path} has not been loaded.")
        if self.size == 0 or top_k <= 0:
            return []
        if self._centroids_dirty or not self._centroid_skus:
            self._build_centroids()

        query = _as_query_matrix(query_vector)[0]
        scores = self._centroids @ query
        order = np.argsort(scores)[::-1][:top_k]
        return [(self._centroid_skus[i], float(scores[i])) for i in order]

    def add(self, sku: str, vector: np.ndarray) -> None:
        """Add one embedding vector for a SKU to the index.

        May be called several times with the same SKU (once per catalog
        image); `search` collapses those rows to the SKU's best score. The
        index is created on the first add, sized to the vector's dimension.
        """
        faiss = _import_faiss()
        matrix = _as_query_matrix(vector)
        if self._index is None:
            self._index = faiss.IndexFlatIP(matrix.shape[1])
            self._id_to_sku = []
        self._index.add(matrix)
        self._id_to_sku.append(sku)
        self._centroids_dirty = True

    def save(self, backend: str | None = None, remove_bg: bool | None = None) -> None:
        """Persist the index, its id map, and how it was built.

        Args:
            backend: Name of the embedding backend used to build these
                vectors. Stored alongside the index so the query side can
                embed with the same model.
            remove_bg: Whether the indexed images were background-removed
                before embedding. Stored so the query side can preprocess
                the same way instead of assuming.
        """
        faiss = _import_faiss()
        if self._index is None:
            raise SearchError("Cannot save an empty FAISS index (nothing added).")
        self._index_path.parent.mkdir(parents=True, exist_ok=True)
        faiss.write_index(self._index, str(self._index_path))
        self._ids_path.write_text(json.dumps(self._id_to_sku), encoding="utf-8")
        if backend or remove_bg is not None:
            meta: dict[str, Any] = {}
            if backend:
                self._backend = backend
                meta["backend"] = backend
            if remove_bg is not None:
                self._remove_bg = remove_bg
                meta["remove_bg"] = remove_bg
            meta["vectors"] = "per_image" if len(self._id_to_sku) != len(set(self._id_to_sku)) else "per_sku"
            self._meta_path.write_text(json.dumps(meta), encoding="utf-8")
        logger.info(
            "Saved FAISS index %s (%d vectors%s)",
            self._index_path.name,
            self.size,
            f", backend={backend}" if backend else "",
        )
