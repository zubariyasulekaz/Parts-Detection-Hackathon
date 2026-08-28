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

# The de-dup script owns what counts as a duplicate; importing keeps the
# measurement and the shipped build on one definition rather than two.
from scripts.rigidhitch_dedup_images import (  # noqa: E402
    keeps_row, load_sharers, variant_root,
)

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
        # np.argmax returns 0 when nothing satisfies the condition, which would
        # silently collapse the index to a single dimension - so ask for the
        # matching positions explicitly and fall back to keeping everything.
        reaching = np.nonzero(cumulative >= (variance if variance is not None else 0.99))[0]
        dims = int(reaching[0]) + 1 if reaching.size else len(singular)
    dims = min(dims, right.shape[0])

    # Epsilon guards the tail components, whose singular values approach zero
    # and would otherwise blow up into pure noise once divided through.
    matrix = right[:dims].T / (singular[:dims] + 1e-5)
    return mean, matrix, dims


def apply_whitener(vectors: np.ndarray, mean: np.ndarray, matrix: np.ndarray) -> np.ndarray:
    """Centre, project, and re-normalize - the same transform for index and query."""
    return unit_rows((vectors - mean) @ matrix)


def apply_filters(rows, vectors, args, sharers=None) -> dict[str, list[int]]:
    """Reproduce the build-time filters, returning surviving row indices per SKU.

    With ``--allow-variant-families`` a shared photo is kept when every SKU
    sharing it is a bundle of the same part, and attributed to all of them: each
    is separately purchasable, so each has to be findable. They are then
    genuinely indistinguishable by photograph, which is correct - they are the
    same object - and ``--family-credit`` scores that honestly.
    """
    zero_mask = np.abs(vectors).sum(axis=1) == 0
    by_sku: dict[str, list[int]] = defaultdict(list)
    for i, row in enumerate(rows):
        if zero_mask[i]:
            continue
        if row["n_skus_sharing"] <= args.max_skus_per_hash:
            by_sku[row["sku"]].append(i)
        elif keeps_row(row, args.max_skus_per_hash, args.allow_variant_families, sharers):
            for sku in (sharers or {}).get(row["sha256"], []):
                by_sku[sku].append(i)

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


def evaluate(
    vectors: np.ndarray,
    by_sku: dict[str, list[int]],
    min_photos: int,
    family_credit: bool = False,
) -> dict:
    """Leave-one-out top-1 / top-3 / top-5 / MRR over the full SKU pool.

    Queries come only from SKUs with at least ``min_photos`` images - a SKU with
    one photo has nothing left to match against once that photo is removed. The
    *pool* is always every SKU, so single-photo products still compete as
    distractors.

    With ``family_credit`` a query is scored against its whole bundle family
    rather than the exact SKU. Once variant families are indexed this is the
    only honest measure: ``BX2619`` and ``BX2619-20`` are one baseplate under
    two part numbers, sharing one photograph, so ranking the sibling first is a
    correct answer being marked wrong. Without the flag the two settings cannot
    be compared - allowing families would appear to lose accuracy purely because
    it introduced siblings that outrank each other.
    """
    skus = sorted(by_sku)
    sku_index = {sku: i for i, sku in enumerate(skus)}
    dim = vectors.shape[1]
    # Integer-coded family per SKU column, so "same part?" is one comparison.
    root_codes = {root: n for n, root in enumerate(sorted({variant_root(s) for s in skus}))}
    roots = np.array([root_codes[variant_root(s)] for s in skus])

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
    margins: list[float] = []
    query_skus: list[str] = []
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
        # Position of the first acceptable answer: the SKU itself, or under
        # family credit any sibling sharing its part number root.
        if family_credit:
            hit = roots[order] == roots[owners][:, None]
            family_ranks = np.argmax(hit, axis=1) + 1
        for position, owner in enumerate(owners):
            ranks.append(int(family_ranks[position]) if family_credit
                         else int(np.where(order[position] == owner)[0][0]) + 1)
            # Gap between the best and second-best product. A narrow gap means
            # the model is not really choosing - it is split between two
            # near-identical parts - which is a far better refusal signal here
            # than the absolute score, whose distributions overlap badly.
            best, second = order[position, 0], order[position, 1]
            margins.append(float(scores[position, best] - scores[position, second]))
            query_skus.append(skus[owner])

    rank_array = np.array(ranks)
    scored_skus = {s for _, s in queries}
    return {
        "queries": len(ranks),
        "skus": len(scored_skus),
        "pool": len(skus),
        "ranks": rank_array,
        "margins": np.array(margins),
        "query_skus": query_skus,
        "top1": float((rank_array == 1).mean() * 100),
        "top3": float((rank_array <= 3).mean() * 100),
        "top5": float((rank_array <= 5).mean() * 100),
        "mrr": float((1.0 / rank_array).mean()),
    }


def load_catalog(path: Path) -> dict[str, tuple[str, bool]]:
    """SKU -> (category, has_fitment) from the catalog CSV.

    Fitment is what splits the catalogue commercially: a product that fits a
    vehicle can be narrowed by the client's existing Year/Make/Model selector,
    while a trailer jack cannot - there is no vehicle to ask about. Those two
    halves must never be averaged together, because they differ by roughly five
    times in how many lookalikes each product has.
    """
    import csv

    catalog: dict[str, tuple[str, bool]] = {}
    with path.open(newline="", encoding="utf-8-sig") as handle:
        for row in csv.DictReader(handle):
            sku = (row.get("sku") or "").strip()
            if sku:
                catalog[sku] = (
                    (row.get("category") or "").strip() or "(uncategorised)",
                    bool((row.get("compatible_vehicles") or "").strip()),
                )
    return catalog


def report_segments(result: dict, catalog: dict[str, tuple[str, bool]]) -> None:
    """Accuracy split by whether a product has vehicle fitment, then by category."""
    ranks, skus = result["ranks"], result["query_skus"]
    has_fitment = np.array([catalog.get(s, ("", False))[1] for s in skus])

    print()
    print("=" * 78)
    print("BY SEGMENT   (never averaged - these two are different problems)")
    print("=" * 78)
    print(f"{'segment':<34}{'queries':>9}{'SKUs':>8}{'top-1':>9}{'top-5':>9}")
    for label, mask in (
        ("universal / trailer (no vehicle)", ~has_fitment),
        ("vehicle-specific (has fitment)", has_fitment),
    ):
        if not mask.any():
            continue
        subset = ranks[mask]
        n_skus = len({s for s, m in zip(skus, mask) if m})
        print(f"{label:<34}{len(subset):>9,}{n_skus:>8,}"
              f"{(subset == 1).mean() * 100:>8.1f}%{(subset <= 5).mean() * 100:>8.1f}%")

    categories = defaultdict(list)
    for rank, sku in zip(ranks, skus):
        categories[catalog.get(sku, ("(unknown)", False))[0]].append(rank)

    ranked = sorted(
        ((c, np.array(r)) for c, r in categories.items() if len(r) >= 50),
        key=lambda kv: -(kv[1] <= 5).mean(),
    )
    print()
    print("BY CATEGORY   (>=50 queries, best top-5 first)")
    print(f"{'category':<44}{'queries':>9}{'top-1':>9}{'top-5':>9}")
    for category, values in ranked:
        print(f"{category[:43]:<44}{len(values):>9,}"
              f"{(values == 1).mean() * 100:>8.1f}%{(values <= 5).mean() * 100:>8.1f}%")


def report_margin(result: dict) -> None:
    """How well the top-1/top-2 gap predicts whether the top answer is right.

    The absolute similarity score has already proved useless as a cutoff here -
    correct and impostor distributions overlap far too much. The *margin* asks a
    different question: is the model actually choosing, or is it split between
    two near-identical parts? That is the case worth turning into a shortlist or
    a vehicle question rather than a confident wrong answer.
    """
    ranks, margins = result["ranks"], result["margins"]
    print()
    print("=" * 78)
    print("TOP-2 MARGIN   (gap between the best and second-best product)")
    print("=" * 78)
    print(f"median margin {np.median(margins):.4f}   "
          f"p10 {np.percentile(margins, 10):.4f}   p90 {np.percentile(margins, 90):.4f}")
    print()
    # Bucketed by percentile rather than absolute value: the margin's scale
    # shifts with dimensionality and whitening, so fixed cutoffs would print an
    # empty table on one configuration and a useless one on another.
    print(f"{'narrowest':>11}{'margin <':>11}{'queries':>10}"
          f"{'top-1 here':>12}{'top-1 rest':>12}{'top-5 here':>12}")
    for pct in (5, 10, 20, 30, 50):
        cut = float(np.percentile(margins, pct))
        narrow = margins <= cut
        if not narrow.any() or narrow.all():
            continue
        print(f"{pct:>10}%{cut:>11.4f}{int(narrow.sum()):>10,}"
              f"{(ranks[narrow] == 1).mean() * 100:>11.1f}%"
              f"{(ranks[~narrow] == 1).mean() * 100:>11.1f}%"
              f"{(ranks[narrow] <= 5).mean() * 100:>11.1f}%")
    print()
    print("Compare 'top-1 here' against 'top-1 rest'. A large drop means a narrow")
    print("gap reliably marks the queries the model gets wrong - so those are the")
    print("ones worth answering with a shortlist or a vehicle question instead of")
    print("a confident guess. Little difference means the margin carries no signal.")


def impostor_sweep(vectors: np.ndarray, by_sku: dict[str, list[int]], rng: np.random.Generator) -> None:
    """Score a sample of queries with their true SKU removed from the pool entirely.

    This is what a genuine out-of-catalog photo looks like - a customer holding a
    brand the client does not stock. Nothing in the index is the right answer, so
    the only honest response is a refusal, and this measures which signal can
    trigger one.

    Two candidate signals are compared on the same queries:

    * **score** - the top similarity. Already known to overlap badly.
    * **margin** - the gap between the best and second-best product. The
      intuition is that when the right answer is present it pulls away from the
      field, and when it is absent the top few are an undifferentiated cluster
      of vaguely-similar parts.

    Both are reported as a refusal rule with its two error rates, because a
    cutoff is only meaningful as a trade: refusing out-of-catalog photos is
    worthless if it also refuses the in-catalog ones.
    """
    skus = sorted(by_sku)
    sku_index = {sku: i for i, sku in enumerate(skus)}
    sums = np.zeros((len(skus), vectors.shape[1]), dtype=np.float32)
    for sku, indices in by_sku.items():
        sums[sku_index[sku]] = vectors[indices].sum(axis=0)
    centroids = unit_rows(sums.copy())

    all_rows = [(i, sku_index[sku]) for sku, idxs in by_sku.items() for i in idxs]
    sample = [all_rows[i] for i in rng.choice(len(all_rows), min(IMPOSTOR_SAMPLE, len(all_rows)), replace=False)]

    # Four parallel arrays: score and margin, under both conditions. The
    # in-catalog margin uses the leave-one-out centroid for the true SKU, so the
    # query is never compared against itself.
    in_score, in_margin, out_score, out_margin = [], [], [], []
    for row, owner in sample:
        vector = vectors[row]
        scores = vector @ centroids.T

        # In-catalog: patch the owner column to its leave-one-out centroid.
        held = sums[owner] - vector
        norm = np.linalg.norm(held)
        loo = float(vector @ (held / norm)) if norm > 1e-6 else -np.inf
        patched = scores.copy()
        patched[owner] = loo
        top2 = np.partition(patched, -2)[-2:]
        in_score.append(float(top2[1]))
        in_margin.append(float(top2[1] - top2[0]))

        # Out-of-catalog: the true SKU is gone from the pool entirely.
        scores[owner] = -np.inf
        top2 = np.partition(scores, -2)[-2:]
        out_score.append(float(top2[1]))
        out_margin.append(float(top2[1] - top2[0]))

    arrays = {k: np.array(v) for k, v in
              (("in_score", in_score), ("in_margin", in_margin),
               ("out_score", out_score), ("out_margin", out_margin))}
    print()
    print("=" * 72)
    print(f"OUT-OF-CATALOG DETECTION   (sample n={len(sample):,})")
    print("=" * 72)
    print("Same queries scored twice: once with the true product in the index,")
    print("once with it removed entirely. A usable refusal signal must separate")
    print("the two columns.")
    print()
    print(f"{'signal':<10}{'in catalog':>26}{'out of catalog':>26}")
    for name in ("score", "margin"):
        a, b = arrays[f"in_{name}"], arrays[f"out_{name}"]
        print(f"{name:<10}"
              f"{f'median {np.median(a):.3f}  p10 {np.percentile(a, 10):.3f}':>26}"
              f"{f'median {np.median(b):.3f}  p90 {np.percentile(b, 90):.3f}':>26}")

    for name in ("score", "margin"):
        a, b = arrays[f"in_{name}"], arrays[f"out_{name}"]
        print()
        print(f"REFUSE WHEN {name.upper()} IS BELOW A CUTOFF")
        print(f"{'cutoff':>10}{'in-catalog refused':>21}{'out-of-catalog caught':>24}")
        # Sweep the cutoff over the observed range rather than a fixed grid: the
        # two signals live on different scales and share no useful thresholds.
        for pct in (1, 2, 5, 10, 20, 30, 50):
            cut = float(np.percentile(a, pct))
            print(f"{cut:>10.4f}{float((a < cut).mean() * 100):>20.1f}%"
                  f"{float((b < cut).mean() * 100):>23.1f}%")
        print("  A useful signal catches far more out-of-catalog photos than the")
        print("  in-catalog ones it sacrifices; equal columns mean no signal at all.")


def main() -> None:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--build-dir", type=Path, default=DEFAULT_BUILD_DIR)
    parser.add_argument("--embeddings", default="embeddings.npy")
    parser.add_argument("--max-skus-per-hash", type=int, default=1)
    parser.add_argument("--allow-variant-families", action="store_true",
                        help="Keep a shared photo when every SKU sharing it is a bundle "
                             "of the same part (BX2619 / BX2619-20 / -70 / -80).")
    parser.add_argument("--family-credit", action="store_true",
                        help="Score a sibling bundle as correct. Required to compare "
                             "against --allow-variant-families fairly.")
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
    parser.add_argument("--catalog", type=Path, default=None,
                        help="catalog.clean.csv, for the segment/category breakdown "
                             "(default: alongside --build-dir).")
    parser.add_argument("--seed", type=int, default=20260827)
    args = parser.parse_args()

    rows = load_rows(args.build_dir / "embed_rows.jsonl")
    vectors = np.load(args.build_dir / args.embeddings).astype(np.float32)
    if len(rows) != vectors.shape[0]:
        raise SystemExit(f"row/vector mismatch: {len(rows):,} vs {vectors.shape[0]:,}")

    sharers = load_sharers(args.build_dir)
    by_sku = apply_filters(rows, vectors, args, sharers)
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
            result = evaluate(matrix, by_sku, minimum, args.family_credit)
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
    scored_label = "raw"
    if args.whiten_sweep:
        report("raw (no whitening)", vectors)
        dims_to_try = [d for d in (64, 128, 256, 384, 512, vectors.shape[1])
                       if d <= vectors.shape[1]]
        for dims in dims_to_try:
            mean, matrix, kept = fit_whitener(tuning_rows, dims, None)
            whitened = apply_whitener(vectors, mean, matrix)
            print("-" * 78)
            report(f"whitened d={kept}", whitened)
            # Carry the last (highest-dimension) variant forward: the sections
            # below must describe what would actually ship, not the raw vectors.
            scored, scored_label = whitened, f"whitened d={kept}"
    elif args.whiten:
        mean, matrix, kept = fit_whitener(tuning_rows, args.whiten_dims, args.whiten_variance)
        scored = apply_whitener(vectors, mean, matrix)
        scored_label = f"whitened d={kept}"
        print(f"({vectors.shape[1]} dims -> {kept} after whitening)")
        report(scored_label, scored)
    else:
        report("raw", vectors)

    print()
    print(f"Ranking pool is all {len(by_sku):,} indexed SKUs, but only multi-photo SKUs")
    print("can be queried. Single-photo products compete as distractors and are")
    print("never scored - so these figures are optimistic about finding *them*.")

    print()
    print(f"### Everything below describes: {scored_label}, 3+ photo slice ###")
    detail = evaluate(scored, by_sku, 3, args.family_credit)
    if detail.get("queries"):
        catalog_path = args.catalog or (args.build_dir.parent / "catalog.clean.csv")
        if catalog_path.is_file():
            report_segments(detail, load_catalog(catalog_path))
        else:
            print(f"\n[skip] segment breakdown - {catalog_path} not found "
                  f"(pass --catalog to point at it)")
        report_margin(detail)

    impostor_sweep(scored, by_sku, np.random.default_rng(args.seed))


if __name__ == "__main__":
    main()
