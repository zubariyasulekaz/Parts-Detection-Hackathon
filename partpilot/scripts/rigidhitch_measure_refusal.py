"""Which signal can refuse an out-of-catalog photo?

A customer photographs a part the client does not stock. Nothing in the index is
the right answer, so the only honest response is "I don't recognise this". This
measures which signal can actually trigger that, by scoring the same queries
twice: once with the true product present, once with it removed from the pool
entirely.

``rigidhitch_eval_index.py --whiten`` already answers this for the two cheap
signals, and the answer is no. Refusing 10% of in-catalog photos catches 17% of
out-of-catalog ones by similarity score, 12.8% by top-2 margin. Both barely beat
chance, because they measure the wrong thing: the margin detects *ambiguity*
(two near-identical parts) which is not the same as *absence*.

So this measures the third candidate, geometric verification, on the identical
split - the comparison is only meaningful against those baselines.

The query is compared against the **candidate's own photographs**, taking the
best pair, not against a centroid: a centroid is an average vector and has no
pixels to match keypoints against. Comparing against a single arbitrary photo
also understates the signal badly - the earlier audit disagreement traced to
exactly that, since a candidate's second photo may be a packaging shot.

Run:
    python scripts/rigidhitch_measure_refusal.py --queries 150
"""

import argparse
import json
import sys
from collections import defaultdict
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from scripts.rigidhitch_geometric_verify import _load_gray, verify  # noqa: E402

DEFAULT_BUILD_DIR = Path(
    r"C:\Users\Vasuki.KLIZER-49\Downloads\rigidhitch_dataset\rigidhitch_dataset\index_build"
)
DEFAULT_IMAGES = Path(
    r"C:\Users\Vasuki.KLIZER-49\Downloads\rigidhitch_dataset\rigidhitch_dataset\images"
)
# Candidates deep in the ranking are never shown to a user, so verifying them
# would measure a decision the product does not make.
TOP_K = 5
# Photos per candidate to try before taking the best. Beyond a handful the extra
# pairs are packaging and instruction sheets.
MAX_PHOTOS = 3


def unit_rows(matrix: np.ndarray) -> np.ndarray:
    norms = np.linalg.norm(matrix, axis=1, keepdims=True)
    return matrix / np.maximum(norms, 1e-12)


def best_inliers(query_path: Path, candidate_photos: list[Path], cache: dict) -> int:
    """Strongest structural agreement between the query and any candidate photo."""
    try:
        query = cache.setdefault(query_path, _load_gray(query_path))
    except SystemExit:
        return -1
    best = 0
    for photo in candidate_photos[:MAX_PHOTOS]:
        try:
            other = cache.setdefault(photo, _load_gray(photo))
        except SystemExit:
            continue
        best = max(best, verify(query, other).inliers)
    return best


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--build-dir", type=Path, default=DEFAULT_BUILD_DIR)
    parser.add_argument("--images", type=Path, default=DEFAULT_IMAGES)
    parser.add_argument("--embeddings", default="embeddings_base.npy")
    parser.add_argument("--queries", type=int, default=150)
    parser.add_argument("--seed", type=int, default=20260828)
    args = parser.parse_args()

    rows = [json.loads(line) for line in
            (args.build_dir / "embed_rows.jsonl").open(encoding="utf-8") if line.strip()]
    vectors = np.load(args.build_dir / args.embeddings).astype(np.float32)
    if len(rows) != len(vectors):
        raise SystemExit(f"manifest has {len(rows):,} rows but embeddings have {len(vectors):,}")

    # Same de-dup rule the shipped index uses; without it a shared stock photo
    # would be counted as a legitimate match.
    keep = [i for i, r in enumerate(rows) if r.get("n_skus_sharing", 1) <= 1]
    rows = [rows[i] for i in keep]
    vectors = unit_rows(vectors[keep])

    by_sku: dict[str, list[int]] = defaultdict(list)
    for i, row in enumerate(rows):
        by_sku[row["sku"]].append(i)

    # Only multi-photo SKUs can be queried: the query photo has to be held out,
    # leaving at least one other photo of the same product to verify against.
    testable = sorted(s for s, idx in by_sku.items() if len(idx) >= 2)
    skus = sorted(by_sku)
    sku_index = {s: i for i, s in enumerate(skus)}
    sums = np.zeros((len(skus), vectors.shape[1]), dtype=np.float32)
    for sku, idx in by_sku.items():
        sums[sku_index[sku]] = vectors[idx].sum(axis=0)
    centroids = unit_rows(sums.copy())

    rng = np.random.default_rng(args.seed)
    chosen = [testable[i] for i in
              rng.choice(len(testable), min(args.queries, len(testable)), replace=False)]

    cache: dict = {}
    in_catalog, out_catalog, unrelated = [], [], []
    for n, sku in enumerate(chosen, 1):
        owner = sku_index[sku]
        row = int(rng.choice(by_sku[sku]))
        query_path = args.images / rows[row]["rel"]
        vector = vectors[row]

        scores = vector @ centroids.T
        # Leave-one-out for the true SKU, so the query never matches itself.
        held = sums[owner] - vector
        norm = np.linalg.norm(held)
        scores[owner] = float(vector @ (held / norm)) if norm > 1e-6 else -np.inf

        siblings = [args.images / rows[i]["rel"] for i in by_sku[sku] if i != row]
        in_catalog.append(best_inliers(query_path, siblings, cache))

        # Out-of-catalog: the true product is gone, so the top-ranked survivor is
        # what the system would show and what it would have to verify.
        scores[owner] = -np.inf
        top = int(np.argmax(scores))
        rival = [args.images / rows[i]["rel"] for i in by_sku[skus[top]]]
        out_catalog.append(best_inliers(query_path, rival, cache))

        # Third arm: a product picked at random rather than the nearest rival.
        # This separates two very different failures. If inliers are low here but
        # high against the rival, verification works and the catalogue's twins
        # are the problem. If they are high here too, the signal is measuring
        # "both are studio photographs on white" and is useless outright.
        other = int(rng.choice(len(skus)))
        while other == owner:
            other = int(rng.choice(len(skus)))
        random_photos = [args.images / rows[i]["rel"] for i in by_sku[skus[other]]]
        unrelated.append(best_inliers(query_path, random_photos, cache))

        if n % 25 == 0:
            print(f"  {n}/{len(chosen)} queries", flush=True)
        if len(cache) > 400:
            cache.clear()

    a = np.array([v for v in in_catalog if v >= 0])
    b = np.array([v for v in out_catalog if v >= 0])
    c = np.array([v for v in unrelated if v >= 0])
    print()
    print("=" * 76)
    print(f"GEOMETRIC VERIFICATION AS A REFUSAL SIGNAL   (n={len(a):,} queries)")
    print("=" * 76)
    print("RANSAC inliers between the query and the best photo of each comparison.")
    print()
    print(f"{'':<22}{'median':>10}{'p10':>10}{'p25':>10}{'p75':>10}{'p90':>10}")
    for name, values in (("true product", a), ("nearest rival", b), ("random product", c)):
        print(f"{name:<22}{np.median(values):>10.0f}"
              f"{np.percentile(values, 10):>10.0f}{np.percentile(values, 25):>10.0f}"
              f"{np.percentile(values, 75):>10.0f}{np.percentile(values, 90):>10.0f}")

    print()
    print("REFUSE WHEN INLIERS ARE BELOW A CUTOFF")
    print(f"{'cutoff':>8}{'true refused':>15}{'rival caught':>15}{'random caught':>16}")
    for cut in (5, 10, 15, 20, 30, 40, 60):
        print(f"{cut:>8}{float((a < cut).mean() * 100):>14.1f}%"
              f"{float((b < cut).mean() * 100):>14.1f}%"
              f"{float((c < cut).mean() * 100):>15.1f}%")
    print()
    print("'true refused' is the cost, the other two columns the benefit. Compare")
    print("against the cheap signals on the same split, where refusing 10% of")
    print("in-catalog photos caught 17% (score) / 12.8% (margin) of strangers.")


if __name__ == "__main__":
    main()
