"""Score retrieval accuracy and calibrate no-match thresholds from the
vectors already stored in the FAISS indexes.

`evaluate_brain2.py` and `calibrate_no_match.py` re-embed every catalog
image, which is the right tool when experimenting with preprocessing — and
takes ~20 minutes of model time. This script instead reconstructs the
per-image vectors out of the built ``backend/models/faiss/*.faiss`` files:
those vectors were produced by the exact production preprocessing (rembg,
TTA, per-category backend), so measuring them measures what the running
system will actually do, in milliseconds.

Scoring matches ``FaissIndex.search`` exactly: each SKU is scored by cosine
against the L2-normalized centroid of its image vectors (centroid ranked
79.1% top-1 vs 72.0% for max-over-images on this catalog — with 2-7 photos
per product, one lucky angle promotes the wrong SKU under max).

Outputs:
  1. Leave-one-out retrieval accuracy (Top-1 / Top-3 / MRR per category),
     scoring each stored image vector as a query against its own category,
     with the query vector excluded from its own product's centroid.
  2. Correct-match vs impostor top-1 score distributions per backend
     (impostors = images of OTHER categories built with the same backend,
     queried against this category), and a threshold sweep with a
     recommendation for ``Settings.NO_MATCH_THRESHOLDS``.

Requires only that the indexes were built (per-image mode). Run:
    python scripts/analyze_index_vectors.py
"""

import json
import sys
from collections import defaultdict
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from backend.config.paths import FAISS_MODEL_DIR  # noqa: E402


def load_indexes() -> dict[str, dict]:
    """slug -> {skus: [sku per row], vectors: (n, dim) array, backend: str}."""
    import faiss  # noqa: PLC0415

    out: dict[str, dict] = {}
    for index_path in sorted(FAISS_MODEL_DIR.glob("*.faiss")):
        slug = index_path.stem
        ids_path = index_path.with_suffix("").parent / f"{slug}.ids.json"
        meta_path = index_path.with_suffix("").parent / f"{slug}.meta.json"
        if not ids_path.exists():
            print(f"[skip] {slug}: no ids sidecar")
            continue
        index = faiss.read_index(str(index_path))
        skus = json.loads(ids_path.read_text(encoding="utf-8"))
        backend = None
        if meta_path.exists():
            backend = json.loads(meta_path.read_text(encoding="utf-8")).get("backend")
        vectors = index.reconstruct_n(0, index.ntotal)
        if len(skus) != vectors.shape[0]:
            print(f"[skip] {slug}: ids/vector count mismatch")
            continue
        if len(skus) == len(set(skus)):
            print(f"[warn] {slug}: one vector per SKU (centroid index?) — "
                  "leave-one-out will skip its single-vector SKUs")
        out[slug] = {"skus": skus, "vectors": vectors, "backend": backend or "unknown"}
    return out


def _unit(vector: np.ndarray) -> np.ndarray:
    norm = np.linalg.norm(vector)
    return vector / norm if norm else vector


def main() -> None:
    indexes = load_indexes()
    if not indexes:
        raise SystemExit(f"No indexes found in {FAISS_MODEL_DIR}")

    # --- 1. leave-one-out retrieval, centroid scoring ---------------------
    per_category: dict[str, dict[str, float]] = {}
    all_ranks: list[int] = []
    misses: list[tuple[str, str, str, float]] = []
    correct_scores: dict[str, list[float]] = defaultdict(list)  # backend -> top-1 correct scores

    for slug, data in sorted(indexes.items()):
        vectors: np.ndarray = data["vectors"]
        skus: list[str] = data["skus"]
        rows_by_sku: dict[str, list[int]] = defaultdict(list)
        for row, sku in enumerate(skus):
            rows_by_sku[sku].append(row)
        ranks: list[int] = []

        for i, true_sku in enumerate(skus):
            if len(rows_by_sku[true_sku]) < 2:
                continue  # nothing left of this SKU once its only vector is held out
            query = vectors[i]
            scores: dict[str, float] = {}
            for sku, rows in rows_by_sku.items():
                pool = [r for r in rows if r != i]
                if not pool:
                    continue
                scores[sku] = float(query @ _unit(vectors[pool].mean(axis=0)))
            ordered = sorted(scores.items(), key=lambda kv: -kv[1])
            rank = next(r for r, (sku, _) in enumerate(ordered, 1) if sku == true_sku)
            ranks.append(rank)
            all_ranks.append(rank)
            correct_scores[data["backend"]].append(ordered[0][1])
            if rank != 1:
                misses.append((true_sku, f"vec{i}", ordered[0][0], ordered[0][1]))

        if ranks:
            n = len(ranks)
            per_category[slug] = {
                "n": n,
                "products": len(set(skus)),
                "backend": data["backend"],
                "top1": sum(r == 1 for r in ranks) / n * 100,
                "top3": sum(r <= 3 for r in ranks) / n * 100,
                "mrr": sum(1 / r for r in ranks) / n,
            }

    print("=" * 78)
    print("BRAIN 2 RETRIEVAL ACCURACY (leave-one-out over stored index vectors)")
    print("=" * 78)
    print(f"{'Category':22}{'Backend':10}{'SKUs':>5}{'Queries':>8}{'Top-1':>9}{'Top-3':>9}{'MRR':>7}")
    print("-" * 78)
    for slug, m in sorted(per_category.items()):
        print(f"{slug:22}{m['backend']:10}{m['products']:>5}{m['n']:>8}"
              f"{m['top1']:>8.1f}%{m['top3']:>8.1f}%{m['mrr']:>7.3f}")
    print("-" * 78)
    n = len(all_ranks)
    print(f"{'OVERALL':22}{'':10}{sum(m['products'] for m in per_category.values()):>5}{n:>8}"
          f"{sum(r == 1 for r in all_ranks) / n * 100:>8.1f}%"
          f"{sum(r <= 3 for r in all_ranks) / n * 100:>8.1f}%"
          f"{sum(1 / r for r in all_ranks) / n:>7.3f}")
    print("=" * 78)
    if misses:
        print(f"\nMisses ({len(misses)}):")
        for true_sku, vec, predicted, score in misses[:20]:
            print(f"   {true_sku:10} {vec:6} -> predicted {predicted:10} ({score:.3f})")

    # --- 2. impostor distribution + threshold sweep, per backend ----------
    centroids_by_slug: dict[str, np.ndarray] = {}
    for slug, data in indexes.items():
        rows_by_sku = defaultdict(list)
        for row, sku in enumerate(data["skus"]):
            rows_by_sku[sku].append(row)
        centroids_by_slug[slug] = np.stack(
            [_unit(data["vectors"][rows].mean(axis=0)) for rows in rows_by_sku.values()]
        )

    impostor_scores: dict[str, list[float]] = defaultdict(list)
    for slug, data in indexes.items():
        spec = data["backend"]
        centroids = centroids_by_slug[slug]
        for other_slug, other in indexes.items():
            if other_slug == slug or other["backend"] != spec:
                continue
            sims = other["vectors"] @ centroids.T  # each foreign image vs this category's centroids
            impostor_scores[spec].extend(np.max(sims, axis=1).tolist())

    recommendations: dict[str, float] = {}
    for spec in sorted(correct_scores):
        c = np.array(correct_scores[spec])
        i = np.array(impostor_scores.get(spec, []))
        print()
        print("=" * 64)
        print(f"BACKEND: {spec}   (correct n={len(c)}, impostor n={len(i)})")
        print("=" * 64)
        print(f"correct:  min {c.min():.3f}  p5 {np.percentile(c, 5):.3f}  "
              f"median {np.median(c):.3f}  max {c.max():.3f}")
        if len(i):
            print(f"impostor: min {i.min():.3f}  median {np.median(i):.3f}  "
                  f"p95 {np.percentile(i, 95):.3f}  max {i.max():.3f}")
        print(f"\n{'threshold':>10}{'correct rejected':>18}{'impostors caught':>18}")
        best_threshold = None
        for t in np.arange(0.30, 0.99, 0.01):
            rejected = float((c < t).mean() * 100)
            caught = float((i < t).mean() * 100) if len(i) else float("nan")
            if rejected == 0.0:
                best_threshold = float(t)
            if round(t * 100) % 5 == 0 or 0 < rejected <= 5:
                print(f"{t:>10.2f}{rejected:>17.1f}%{caught:>17.1f}%")
            if rejected > 5:
                break
        if best_threshold is not None:
            caught_at = float((i < best_threshold).mean() * 100) if len(i) else float("nan")
            recommendations[spec] = round(best_threshold, 2)
            print(f"\nRecommended: {best_threshold:.2f} "
                  f"(highest threshold rejecting 0% of correct matches; "
                  f"catches {caught_at:.1f}% of impostors)")

    if recommendations:
        print("\nSettings.NO_MATCH_THRESHOLDS suggestion:")
        print("    NO_MATCH_THRESHOLDS: dict[str, float] = " + json.dumps(recommendations, indent=8))


if __name__ == "__main__":
    main()
