"""Manages the collection of per-category FAISS indexes.

At 100k+ product scale, a single flat index is impractical to search
per-category; instead each category gets its own `FaissIndex`, looked up
by the classifier's predicted category.
"""

import re
from pathlib import Path

from backend.config.settings import get_settings
from backend.core.exceptions import SearchError
from backend.core.logging import get_logger
from backend.pipeline.brain2_similarity.faiss_index import FaissIndex

logger = get_logger(__name__)


def category_slug(category: str) -> str:
    """Normalize a category name to a filesystem-safe index slug.

    Ensures the build side and the query side agree on index filenames
    regardless of casing/spacing, e.g. both ``"Brake Pads"`` and the
    classifier label ``"brake_pad"`` need to resolve consistently. Here
    ``"Brake Pads"`` -> ``"brake_pads"``.
    """
    slug = re.sub(r"[^a-z0-9]+", "_", category.strip().lower())
    return slug.strip("_")


class IndexManager:
    """Loads and caches one `FaissIndex` per product category."""

    def __init__(self, index_dir: Path | None = None) -> None:
        self._index_dir = index_dir or Path(get_settings().RIGIDHITCH_FAISS_PATH)
        self._indexes: dict[str, FaissIndex] = {}

    def get_index(self, category: str) -> FaissIndex:
        """Return the (lazily loaded) FAISS index for a category.

        Args:
            category: Product category, as predicted by Brain 1.

        Raises:
            backend.core.exceptions.SearchError: If no index file exists
                for the given category.
        """
        if category not in self._indexes:
            index_path = self._index_dir / f"{category_slug(category)}.faiss"
            if not index_path.exists():
                # TODO: Once indexes are built, decide whether a missing
                # category index should raise or fall back to a global index.
                raise SearchError(f"No FAISS index found for category '{category}'.")
            index = FaissIndex(index_path)
            index.load()
            self._indexes[category] = index
        return self._indexes[category]

    def list_available_categories(self) -> list[str]:
        """List categories that currently have a built FAISS index on disk."""
        if not self._index_dir.exists():
            return []
        return sorted(p.stem for p in self._index_dir.glob("*.faiss"))
