"""Filter the cached vectors and build RigidHitch's flat search index.

Runs on the embeddings produced by ``rigidhitch_embed_images.py`` - no GPU, no
model load, seconds rather than an hour. That is the point of caching vectors:
both filters and every threshold can be re-tuned without re-embedding.

Two filters, applied in order:

**Cross-SKU images.** ``n_skus_sharing`` from the row manifest. A photo used by
two products cannot distinguish them; one used by 367 is a placeholder. The
cutoff is a flag, not a constant, because "two SKUs" is often a legitimate
left/right variant and "367" plainly is not.

**Kit photos.** Some catalog frames show the whole kit laid out - a bag of
bolts, brackets and an instruction sheet - rather than the product. They match
nothing a customer photographs, and they resemble every *other* kit photo, so
they actively pull up wrong products. They are found by comparing each image to
the mean of its own product's other images: genuine shots score 0.82-0.95
against their siblings, kit shots 0.21-0.28.

Only applied at ``--kit-min-siblings`` (default 3) or more images. With exactly
two, "mean of siblings excluding self" collapses to the single other photo, so
the score is just the pairwise cosine and there is no way to tell which of the
two is the kit shot. Those pairs are scored and reported, never dropped.

The index is written to its own directory and searched with a sentinel category
name, so PartPilot's own per-category indexes are untouched:

    IndexManager(index_dir=Path("backend/models/faiss_rigidhitch"))
    service.search("rigidhitch", image)

Run:
    python scripts/rigidhitch_filter_and_build.py
    python scripts/rigidhitch_filter_and_build.py --kit-threshold 0.35 --max-skus-per-hash 2
"""

import argparse
import hashlib
import json
import sys
from collections import defaultdict
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

# One definition of "duplicate", shared with the de-dup script and the eval.
from scripts.rigidhitch_dedup_images import keeps_row, load_sharers  # noqa: E402

from backend.pipeline.brain2_similarity.faiss_index import FaissIndex  # noqa: E402
from rigidhitch_eval_index import apply_whitener, fit_whitener  # noqa: E402

DEFAULT_BUILD_DIR = Path(
    r"C:\Users\Vasuki.KLIZER-49\Downloads\rigidhitch_dataset\rigidhitch_dataset\index_build"
)
DEFAULT_INDEX_DIR = Path(__file__).resolve().parent.parent / "backend" / "models" / "faiss_rigidhitch"
INDEX_NAME = "rigidhitch"
KIT_THRESHOLD = 0.40
KIT_MIN_SIBLINGS = 3


def load_rows(path: Path) -> list[dict]:
    with path.open(encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]


def check_binding(rows_path: Path, meta: dict) -> None:
    """Refuse to build if the vectors were not produced from these exact rows.

    Row N of the array must be line N of the manifest. If the manifest has been
    regenerated since embedding, that correspondence is silently wrong and every
    vector would be attributed to the wrong SKU - an index that looks fine and
    is entirely garbage. Better to stop.
    """
    actual = hashlib.sha256(rows_path.read_bytes()).hexdigest()
    expected = meta.get("rows_file_sha256")
    if expected and actual != expected:
        raise SystemExit(
            "Row manifest does not match the one used for embedding.\n"
            f"  embeddings.meta.json expects : {expected[:16]}...\n"
            f"  {rows_path.name} is          : {actual[:16]}...\n"
            "Re-run rigidhitch_embed_images.py, or restore the original manifest."
        )


def kit_scores(vectors: np.ndarray, indices: list[int]) -> np.ndarray:
    """Cosine of each vector against the mean of its siblings, excluding itself.

    Vectors are unit length, so the sibling mean only needs re-normalizing:
    ``cos(v_i, unit(S - v_i))`` where ``S`` is the SKU's vector sum.
    """
    block = vectors[indices]
    total = block.sum(axis=0)
    sibling_sums = total - block
    norms = np.linalg.norm(sibling_sums, axis=1, keepdims=True)
    norms[norms == 0] = 1.0
    return np.einsum("ij,ij->i", block, sibling_sums / norms)


def main() -> None:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--build-dir", type=Path, default=DEFAULT_BUILD_DIR)
    parser.add_argument("--index-dir", type=Path, default=DEFAULT_INDEX_DIR)
    parser.add_argument("--embeddings", default="embeddings.npy",
                        help="Array filename within --build-dir (default: embeddings.npy)")
    parser.add_argument("--allow-variant-families", action="store_true",
                        help="Keep a shared photo when every SKU sharing it is a bundle "
                             "of one part (BX2619 / BX2619-20 / -70 / -80), and index it "
                             "for all of them. Recovers ~1,300 products.")
    parser.add_argument("--max-skus-per-hash", type=int, default=1,
                        help="Keep an image only if its content is used by at most this "
                             "many SKUs (default: 1).")
    parser.add_argument("--kit-threshold", type=float, default=KIT_THRESHOLD,
                        help=f"Drop images scoring below this against their siblings "
                             f"(default: {KIT_THRESHOLD}).")
    parser.add_argument("--kit-min-siblings", type=int, default=KIT_MIN_SIBLINGS,
                        help=f"Only run the kit filter on SKUs with at least this many "
                             f"images (default: {KIT_MIN_SIBLINGS}).")
    parser.add_argument("--no-kit-filter", action="store_true",
                        help="Skip the kit filter entirely (for measuring its effect).")
    parser.add_argument("--no-whiten", action="store_true",
                        help="Build without PCA whitening. Measured at -17.9 points "
                             "top-5, so only useful for comparison.")
    parser.add_argument("--dry-run", action="store_true",
                        help="Report what would be filtered; write nothing.")
    args = parser.parse_args()

    rows_path = args.build_dir / "embed_rows.jsonl"
    array_path = args.build_dir / args.embeddings
    meta_path = array_path.with_suffix("").with_suffix(".meta.json")
    if not meta_path.is_file():
        meta_path = args.build_dir / (array_path.stem + ".meta.json")

    for path in (rows_path, array_path, meta_path):
        if not path.is_file():
            raise SystemExit(f"missing: {path}")

    meta = json.loads(meta_path.read_text())
    check_binding(rows_path, meta)

    rows = load_rows(rows_path)
    sharers = load_sharers(args.build_dir)
    vectors = np.load(array_path).astype(np.float32)
    if len(rows) != vectors.shape[0]:
        raise SystemExit(
            f"row/vector count mismatch: {len(rows):,} rows vs {vectors.shape[0]:,} vectors"
        )

    # A failed image was written as a zero vector to keep the array aligned;
    # it carries no information and must not reach the index.
    zero_mask = np.abs(vectors).sum(axis=1) == 0
    shared_mask = np.array([
        not keeps_row(r, args.max_skus_per_hash, args.allow_variant_families, sharers)
        for r in rows
    ])
    keep = ~zero_mask & ~shared_mask

    # A photo kept because it belongs to a bundle family is attributed to every
    # SKU in that family - each is separately purchasable, so each has to be
    # findable. Without this, BX2619 stays unfindable while its -20/-70/-80
    # bundles remain, which is the wrong way round: the base part is what a
    # customer photographs.
    by_sku: dict[str, list[int]] = defaultdict(list)
    for i, row in enumerate(rows):
        if not keep[i]:
            continue
        if row["n_skus_sharing"] <= args.max_skus_per_hash:
            by_sku[row["sku"]].append(i)
        else:
            for sku in sharers.get(row["sha256"], []):
                by_sku[sku].append(i)

    kit_dropped: list[int] = []
    pair_scores: list[dict] = []
    scored: list[dict] = []

    if not args.no_kit_filter:
        for sku, indices in by_sku.items():
            if len(indices) < 2:
                continue
            scores = kit_scores(vectors, indices)
            if len(indices) < args.kit_min_siblings:
                # Two photos: the score is just their pairwise cosine and cannot
                # say which one is the kit shot. Record it, drop neither.
                pair_scores.append({"sku": sku, "cosine": round(float(scores[0]), 4)})
                continue
            for position, index in enumerate(indices):
                score = float(scores[position])
                scored.append({"row": index, "sku": sku, "sibling_cos": round(score, 4)})
                if score < args.kit_threshold:
                    kit_dropped.append(index)

    for index in kit_dropped:
        keep[index] = False

    # Rebuilt with the same family expansion used above. Reading `row["sku"]`
    # alone here would silently discard it: the sibling bundles would vanish
    # from the index while still counting as "emptied by the kit filter", and
    # the build would ship a different SKU set from the one the eval measured.
    final_by_sku: dict[str, list[int]] = defaultdict(list)
    for i, row in enumerate(rows):
        if not keep[i]:
            continue
        if row["n_skus_sharing"] <= args.max_skus_per_hash:
            final_by_sku[row["sku"]].append(i)
        else:
            for sku in sharers.get(row["sha256"], []):
                final_by_sku[sku].append(i)

    emptied_by_kit = sorted(set(by_sku) - set(final_by_sku))

    print(f"rows                : {len(rows):,}")
    print(f"  zero vectors      : {int(zero_mask.sum()):,} (failed images)")
    print(f"  shared across SKUs: {int(shared_mask.sum()):,} "
          f"(--max-skus-per-hash {args.max_skus_per_hash})")
    if args.no_kit_filter:
        print("  kit filter        : skipped")
    else:
        print(f"  kit photos        : {len(kit_dropped):,} dropped of {len(scored):,} scored "
              f"(threshold {args.kit_threshold}, min siblings {args.kit_min_siblings})")
        print(f"  2-photo SKUs      : {len(pair_scores):,} scored, none dropped")
    # Counted from final_by_sku, not `keep`: a photo shared by a bundle family
    # is indexed once per sibling SKU, so the number of index entries exceeds
    # the number of surviving images.
    index_entries = sum(len(v) for v in final_by_sku.values())
    print(f"indexed vectors     : {index_entries:,} entries from {int(keep.sum()):,} "
          f"distinct images, across {len(final_by_sku):,} SKUs")
    if emptied_by_kit:
        print(f"  [warn] {len(emptied_by_kit)} SKU(s) lost every image to the kit filter")

    if args.dry_run:
        print("\nDry run - nothing written.")
        return

    # Whitening, fitted on the tuning split only and then applied to everything.
    # Worth +17.9 points top-5, so an index built without it throws away most of
    # what the pipeline achieves. The transform is persisted next to the index:
    # a query photo must be rebalanced by the *same* matrix or its vector is not
    # comparable to the stored ones at all.
    whiten_meta: dict | None = None
    if not args.no_whiten:
        split_path = args.build_dir / "split.json"
        if not split_path.is_file():
            raise SystemExit(
                f"{split_path} not found - needed to fit whitening on the tuning half "
                f"only. Re-run rigidhitch_dedup_images.py, or pass --no-whiten."
            )
        tuning = set(json.loads(split_path.read_text())["tuning_skus"])
        train_indices = [i for sku, idxs in final_by_sku.items() if sku in tuning for i in idxs]
        if len(train_indices) < 100:
            raise SystemExit(f"only {len(train_indices)} tuning vectors - too few to fit whitening.")

        # Keep every component: the sweep measured accuracy still climbing at the
        # full dimension count (768 base / 1024 large), so there is nothing to gain
        # by truncating. Passed explicitly rather than as a variance target.
        w_mean, w_matrix, w_dims = fit_whitener(vectors[train_indices], vectors.shape[1], None)
        vectors = apply_whitener(vectors, w_mean, w_matrix)
        whiten_meta = {"dims": w_dims, "fitted_on_vectors": len(train_indices)}
        print(f"whitening           : fitted on {len(train_indices):,} tuning vectors "
              f"-> {w_dims} dims")

    args.build_dir.mkdir(parents=True, exist_ok=True)
    (args.build_dir / "filter.kit.json").write_text(json.dumps({
        "threshold": args.kit_threshold,
        "min_siblings": args.kit_min_siblings,
        "enabled": not args.no_kit_filter,
        "dropped_rows": sorted(kit_dropped),
        "skus_emptied_by_kit_filter": emptied_by_kit,
        "scores": scored,
        "two_photo_pair_scores": pair_scores,
    }, indent=2))

    args.index_dir.mkdir(parents=True, exist_ok=True)
    index = FaissIndex(args.index_dir / f"{INDEX_NAME}.faiss")
    # Driven by final_by_sku, not the raw rows: it is the only structure that
    # carries both filters *and* the family expansion, so it is what the eval
    # scored. Adding from `rows` instead would ship an index nobody measured.
    for sku, indices in sorted(final_by_sku.items()):
        for i in indices:
            index.add(sku, vectors[i])
    # remove_bg=True: a customer's garage photo always needs background removal,
    # and the catalog vectors live on white. rembg on an already-white image is
    # near-idempotent, so the ~20% that were actually processed and the ~80% that
    # were already clean sit in the same distribution.
    index.save(backend=meta["backend"], remove_bg=True)

    if whiten_meta is not None:
        # The query side is useless without these two arrays - saved as one .npz
        # beside the index so they cannot drift apart from it.
        np.savez(args.index_dir / f"{INDEX_NAME}.whiten.npz", mean=w_mean, matrix=w_matrix)

    # FaissIndex records backend and remove_bg but not TTA. If a rebuild ever
    # disagrees with the runtime's EMBEDDING_TTA the vectors mismatch silently,
    # so the full build configuration is written alongside it.
    (args.index_dir / f"{INDEX_NAME}.build.json").write_text(json.dumps({
        "backend": meta["backend"],
        "tta": meta["tta"],
        "dim": meta["dim"],
        "remove_bg": True,
        "whitening": whiten_meta,
        "rows_file_sha256": meta["rows_file_sha256"],
        "max_skus_per_hash": args.max_skus_per_hash,
        "allow_variant_families": args.allow_variant_families,
        "kit_threshold": args.kit_threshold if not args.no_kit_filter else None,
        "kit_min_siblings": args.kit_min_siblings,
        "indexed_vectors": int(keep.sum()),
        "indexed_skus": len(final_by_sku),
    }, indent=2))

    print(f"\nWrote {INDEX_NAME}.faiss (+ sidecars) -> {args.index_dir}")
    if whiten_meta is not None:
        print(f"Wrote {INDEX_NAME}.whiten.npz - a query photo MUST be transformed")
        print("with this before searching, or its vector is not comparable.")
    print(f"Wrote filter.kit.json -> {args.build_dir}")
    print(f'\nSearch it with: IndexManager(index_dir=Path(r"{args.index_dir}"))'
          f' then search("{INDEX_NAME}", image)')


if __name__ == "__main__":
    main()
