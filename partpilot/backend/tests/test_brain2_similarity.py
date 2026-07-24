"""Tests for Brain 2 similarity search building blocks.

The FAISS round-trip test is skipped where ``faiss`` is not installed, so it
still exercises real behavior in Colab/CI where the dependency is present.
"""

from pathlib import Path

import numpy as np
import pytest

from backend.pipeline.brain2_similarity.faiss_index import FaissIndex, _as_query_matrix
from backend.pipeline.brain2_similarity.index_manager import category_slug


def test_category_slug_normalizes_spacing_and_case() -> None:
    assert category_slug("Brake Pads") == "brake_pads"
    assert category_slug("Oil Filter") == "oil_filter"
    assert category_slug("  Cabin/AC Filter  ") == "cabin_ac_filter"


def test_query_matrix_is_unit_normalized_float32() -> None:
    matrix = _as_query_matrix(np.array([3.0, 4.0]))
    assert matrix.shape == (1, 2)
    assert matrix.dtype == np.float32
    assert np.isclose(np.linalg.norm(matrix), 1.0)


def test_query_matrix_handles_zero_vector() -> None:
    matrix = _as_query_matrix(np.zeros(4))
    assert not np.isnan(matrix).any()


def test_faiss_index_roundtrip(tmp_path: Path) -> None:
    pytest.importorskip("faiss")

    index = FaissIndex(tmp_path / "brake_pads.faiss")
    vectors = {
        "BP001": np.array([1.0, 0.0, 0.0]),
        "BP002": np.array([0.0, 1.0, 0.0]),
        "BP003": np.array([0.0, 0.0, 1.0]),
    }
    for sku, vec in vectors.items():
        index.add(sku, vec)
    index.save()

    # Reload from disk and query with a vector closest to BP002.
    loaded = FaissIndex(tmp_path / "brake_pads.faiss")
    loaded.load()
    assert loaded.size == 3

    results = loaded.search(np.array([0.1, 0.9, 0.0]), top_k=2)
    assert results[0][0] == "BP002"
    assert 0.9 <= results[0][1] <= 1.0
    assert len(results) == 2


def test_faiss_search_requires_load(tmp_path: Path) -> None:
    from backend.core.exceptions import SearchError

    index = FaissIndex(tmp_path / "missing.faiss")
    with pytest.raises(SearchError):
        index.search(np.array([1.0, 0.0]), top_k=1)
