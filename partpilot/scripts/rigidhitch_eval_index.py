"""Measure RigidHitch retrieval accuracy from the cached vectors.

Reads ``embeddings.npy`` and the manifests directly rather than the built
index, so a filter setting or threshold can be scored without rebuilding
anything. Applies the same two filters as ``rigidhitch_filter_and_build.py``,
driven by the same flags, so what is measured is what would be shipped.

Scoring is leave-one-out: each image is used as a query against per-SKU
centroids, with that image removed from its own SKU's centroid first. Nothing
is ever matched against itself. Because vectors are unit length, the LOO
centroid is ``unit(S_s - v_i)`` where ``S_s`` is the SKU's vector sum, so the
whole thing is one chunked matmul with a single column patched per query -
seconds, not the O(n^2) Python loop the existing per-category script uses.

The existing ``analyze_index_vectors.py`` cannot be reused here: it globs one
index file per category and its impostor sweep needs at least two of them.

Two reporting rules, both load-bearing:

* Results are reported per slice and **never averaged**, because only
  multi-photo SKUs can be scored at all while the ranking pool holds every
  indexed SKU. Single-photo products act as realistic distractors but are never
  themselves queried, so top-1 flatters how findable *they* are.
* Sample size is printed beside every figure.

Run:
    python scripts/rigidhitch_eval_index.py
    python scripts/rigidhitch_eval_index.py --no-kit-filter    # measure its effect
"""

import argparse
import json
import sys
from collections import defaultdict
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

DEFAULT_BUILD_DIR = Path(
    r"C:\Users\Vasuki.KLIZER-49\Downloads\rigidhitch_dataset\rigidhitch_dataset\index_build"
)
CHUNK = 512
IMPOSTOR_SAMPLE = 2000


def load_rows(path: Path) -> list[dict]:
    with path.open(encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]


def unit_rows(matrix: np.ndarray) -> np.ndarray:
    norms = np.linalg.norm(matrix, axis=1, keepdims=True)
    norms[norms == 0] = 1.0
    return matrix / norms


def kit_scores(vectors: np.ndarray, indices: list[int]) -> np.ndarray:
    """Cosine of each vector against the mean of its siblings, excluding itself."""
    block = vectors[indices]
    sibling_sums = block.sum(axis=0) - block
    return np.einsum("ij,ij->i", block, unit_rows(sibling_sums))


def fit_whitener(train: np.ndarray, dims: int | None, variance: float | None) -> tuple:
    """Fit a PCA whitening transform on the tuning vectors only.

    DINOv2's dimensions are correlated and wildly unequal in variance: a few
    directions carrying overall brightness and canonical product pose dominate
    the cosine, drowning out the fine geometry that separates one hitch from
    another. Whitening rescales every retained direction to unit variance, so
    the small discriminative differences count as much as the large generic
    ones.

    Fitted on the tuning split alone. Fitting on everything would let the
    transform see the SKUs it is later scored on - a mild leak, since PCA uses
    no labels, but the split exists precisely so no such question arises.

    The usual ``sqrt(n-1)`` scale factor is omitted: it multiplies every
    dimension equally, so L2 normalization afterwards cancels it out.
    """
    mean = train.mean(axis=0)
    _, singular, right = np.linalg.svd(train - mean, full_matrices=False)

    if dims is None:
        explained = singular**2
        cumulative = np.cumsum(explained) / explained.sum()
        dims = int(np.argmax(cumulative >= (variance or 0.99)) + 1)
    dims = min(dims, right.shape[0])

    # Epsilon guards the tail components, whose singular values approach zero
    # and would otherwise blow up into pure noise once divided through.
    matrix = right[:dims].T / (singular[:dims] + 1e-5)
    return mean, matrix, dims


def apply_whitener(vectors: np.ndarray, mean: np.ndarray, matrix: np.ndarray) -> np.ndarray:
    """Centre, project, and re-normalize - the same transform for index and query."""
    return unit_rows((vectors - mean) @ matrix)


def apply_filters(rows, vectors, args) -> dict[str, list[int]]:
    """Reproduce the build-time filters, returning surviving row indices per SKU."""
    zero_mask = np.abs(vectors).sum(axis=1) == 0
    by_sku: dict[str, list[int]] = defaultdict(list)
    for i, row in enumerate(rows):
        if zero_mask[i] or row["n_skus_sharing"] > args.max_skus_per_hash:
            continue
        by_sku[row["sku"]].append(i)

    if args.no_kit_filter:
        return by_sku

    filtered: dict[str, list[int]] = {}
    for sku, indices in by_sku.items():
        if len(indices) >= args.kit_min_siblings:
            scores = kit_scores(vectors, indices)
            kept = [i for i, s in zip(indices, scores) if s >= args.kit_threshold]
        else:
            kept = indices
        if kept:
            filtered[sku] = kept
    return filtered


def evaluate(vectors: np.ndarray, by_sku: dict[str, list[int]], min_photos: int) -> dict:
    """Leave-one-out top-1 / top-3 / top-5 / MRR over the full SKU pool.

    Queries come only from SKUs with at least ``min_photos`` images - a SKU with
    one photo has nothing left to match against once that photo is removed. The
    *pool* is always every SKU, so single-photo products still compete as
    distractors.
    """
    skus = sorted(by_sku)
    sku_index = {sku: i for i, sku in enumerate(skus)}
    dim = vectors.shape[1]

    sums = np.zeros((len(skus), dim), dtype=np.float32)
    counts = np.zeros(len(skus), dtype=np.int32)
    for sku, indices in by_sku.items():
        sums[sku_index[sku]] = vectors[indices].sum(axis=0)
        counts[sku_index[sku]] = len(indices)

    centroids = unit_rows(sums.copy())

    queries: list[tuple[int, int]] = []  # (row index, sku index)
    for sku, indices in by_sku.items():
        if len(indices) >= min_photos:
            queries.extend((i, sku_index[sku]) for i in indices)

    if not queries:
        return {"queries": 0, "skus": 0}

    ranks: list[int] = []
    for start in range(0, len(queries), CHUNK):
        block = queries[start : start + CHUNK]
        rows = np.array([q for q, _ in block])
        owners = np.array([s for _, s in block])
        query_vectors = vectors[rows]

        scores = query_vectors @ centroids.T

        # Patch each query's own SKU column: recompute its centroid without
        # this vector, so an image is never scored against itself.
        loo_sums = sums[owners] - query_vectors
        loo = unit_rows(loo_sums)
        own = np.einsum("ij,ij->i", query_vectors, loo)
        # A SKU with exactly one surviving image has no sibling left; it cannot
        # be its own answer, so it drops out of contention for that query.
        own[counts[owners] <= 1] = -np.inf
        scores[np.arange(len(block)), owners] = own

        order = np.argsort(-scores, axis=1)
        for position, owner in enumerate(owners):
            ranks.append(int(np.where(order[position] == owner)[0][0]) + 1)

    rank_array = np.array(ranks)
    scored_skus = {s for _, s in queries}
    return {
        "queries": len(ranks),
        "skus": len(scored_skus),
        "pool": len(skus),
        "top1": float((rank_array == 1).mean() * 100),
        "top3": float((rank_array <= 3).mean() * 100),
        "top5": float((rank_array <= 5).mean() * 100),
        "mrr": float((1.0 / rank_array).mean()),
    }


def impostor_sweep(vectors: np.ndarray, by_sku: dict[str, list[int]], rng: np.random.Generator) -> None:
    """Score a sample of queries with their true SKU removed from the pool entirely.

    This is what a genuine out-of-catalog photo looks like: nothing in the index
    is the right answer. The gap between these scores and correct-match scores
    is what any similarity threshold would have to separate.
    """
    skus = sorted(by_sku)
    sku_index = {sku: i for i, sku in enumerate(skus)}
    sums = np.zeros((len(skus), vectors.shape[1]), dtype=np.float32)
    for sku, indices in by_sku.items():
        sums[sku_index[sku]] = vectors[indices].sum(axis=0)
    centroids = unit_rows(sums.copy())

    all_rows = [(i, sku_index[sku]) for sku, idxs in by_sku.items() for i in idxs]
    sample = [all_rows[i] for i in rng.choice(len(all_rows), min(IMPOSTOR_SAMPLE, len(all_rows)), replace=False)]

    correct, impostor = [], []
    for row, owner in sample:
        scores = vectors[row] @ centroids.T
        correct.append(float(scores[owner]))
        scores[owner] = -np.inf  # remove the true answer: now nothing is right
        impostor.append(float(scores.max()))

    c, i = np.array(correct), np.array(impostor)
    print()
    print("=" * 66)
    print(f"IMPOSTOR SEPARATION   (sample n={len(sample):,})")
    print("=" * 66)
    print(f"correct match : median {np.median(c):.3f}   p5 {np.percentile(c, 5):.3f}")
    print(f"best wrong    : median {np.median(i):.3f}   p95 {np.percentile(i, 95):.3f}")
    overlap = float((i > np.median(c)).mean() * 100)
    print(f"\n{overlap:.1f}% of wrong answers score above the median correct match.")
    if np.median(i) >= np.median(c):
        print("The score points the WRONG WAY - a similarity cutoff cannot separate")
        print("these. Refusal needs a second signal (geometric verification).")
    else:
        print(f"\n{'threshold':>10}{'correct rejected':>18}{'impostors caught':>18}")
        for t in np.arange(0.30, 0.99, 0.02):
            rejected = float((c < t).mean() * 100)
            caught = float((i < t).mean() * 100)
            if rejected <= 10:
                print(f"{t:>10.2f}{rejected:>17.1f}%{caught:>17.1f}%")
            if rejected > 10:
                break


def main() -> None:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--build-dir", type=Path, default=DEFAULT_BUILD_DIR)
    parser.add_argument("--embeddings", default="embeddings.npy")
    parser.add_argument("--max-skus-per-hash", type=int, default=1)
    parser.add_argument("--kit-threshold", type=float, default=0.40)
    parser.add_argument("--kit-min-siblings", type=int, default=3)
    parser.add_argument("--no-kit-filter", action="store_true")
    parser.add_argument("--whiten", action="store_true",
                        help="Apply PCA whitening, fitted on the tuning split only.")
    parser.add_argument("--whiten-dims", type=int, default=None,
                        help="Keep this many components (default: enough for --whiten-variance).")
    parser.add_argument("--whiten-variance", type=float, default=0.99,
                        help="Variance to retain when --whiten-dims is unset (default: 0.99).")
    parser.add_argument("--whiten-sweep", action="store_true",
                        help="Score several component counts and the un-whitened baseline.")
    parser.add_argument("--seed", type=int, default=20260827)
    args = parser.parse_args()

    rows = load_rows(args.build_dir / "embed_rows.jsonl")
    vectors = np.load(args.build_dir / args.embeddings).astype(np.float32)
    if len(rows) != vectors.shape[0]:
        raise SystemExit(f"row/vector mismatch: {len(rows):,} vs {vectors.shape[0]:,}")

    by_sku = apply_filters(rows, vectors, args)
    total_vectors = sum(len(v) for v in by_sku.values())

    print(f"indexed: {total_vectors:,} vectors across {len(by_sku):,} SKUs")
    print(f"filters: max-skus-per-hash={args.max_skus_per_hash}  "
          f"kit={'off' if args.no_kit_filter else f'<{args.kit_threshold} at >={args.kit_min_siblings} imgs'}")

    tuning_rows: np.ndarray | None = None
    if args.whiten or args.whiten_sweep:
        split_path = args.build_dir / "split.json"
        if not split_path.is_file():
            raise SystemExit(f"{split_path} not found - re-run rigidhitch_dedup_images.py.")
        tuning = set(json.loads(split_path.read_text())["tuning_skus"])
        indices = [i for sku, idxs in by_sku.items() if sku in tuning for i in idxs]
        if len(indices) < 100:
            raise SystemExit(f"only {len(indices)} tuning vectors - too few to fit whitening.")
        tuning_rows = vectors[indices]
        print(f"whitening fitted on {len(indices):,} tuning vectors "
              f"({len(tuning & set(by_sku)):,} SKUs), never on the test half")

    def report(label: str, matrix: np.ndarray) -> None:
        for slice_label, minimum in (("2+ photos", 2), ("3+ photos", 3)):
            result = evaluate(matrix, by_sku, minimum)
            if not result.get("queries"):
                continue
            print(f"{label:<20}{slice_label:<12}{result['queries']:>8,}{result['skus']:>7,}"
                  f"{result['top1']:>8.1f}%{result['top3']:>8.1f}%{result['top5']:>8.1f}%"
                  f"{result['mrr']:>8.3f}")

    print()
    print("=" * 78)
    print(f"{'variant':<20}{'slice':<12}{'queries':>8}{'SKUs':>7}"
          f"{'top-1':>8}{'top-3':>8}{'top-5':>8}{'MRR':>8}")
    print("=" * 78)

    scored = vectors
    if args.whiten_sweep:
        report("raw (no whitening)", vectors)
        for dims in (64, 128, 256, 384, 512):
            if dims >= vectors.shape[1]:
                continue
            mean, matrix, kept = fit_whitener(tuning_rows, dims, None)
            print("-" * 78)
            report(f"whitened d={kept}", apply_whitener(vectors, mean, matrix))
    elif args.whiten:
        mean, matrix, kept = fit_whitener(tuning_rows, args.whiten_dims, args.whiten_variance)
        scored = apply_whitener(vectors, mean, matrix)
        print(f"({vectors.shape[1]} dims -> {kept} after whitening)")
        report(f"whitened d={kept}", scored)
    else:
        report("raw", vectors)

    print()
    print(f"Ranking pool is all {len(by_sku):,} indexed SKUs, but only multi-photo SKUs")
    print("can be queried. Single-photo products compete as distractors and are")
    print("never scored - so these figures are optimistic about finding *them*.")

    impostor_sweep(scored, by_sku, np.random.default_rng(args.seed))


if __name__ == "__main__":
    main()
