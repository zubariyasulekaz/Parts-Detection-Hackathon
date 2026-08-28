"""De-duplicate RigidHitch's catalog images and emit the embedding row manifest.

Magento stores one image file at many paths, so the same photograph is filed
under many SKUs. Measured across the full corpus: only 17,103 of the 27,297
files are distinct by content, 1,993 hashes are shared across more than one
SKU, and one single file is used by 367 different products. Removing those
(plus kit photos, handled later in rigidhitch_filter_and_build.py) is what
took a category audit from 10.2% to 54.6% top-1 - by a wide margin the
highest-value work available.

Two things are dropped, for different reasons:

* Exact repeats of the same content *within* one SKU - embedding the same
  bytes twice yields the same vector, so the copies are pure waste.
* Images whose content is shared *across* SKUs - a photo used by two products
  cannot distinguish them, and one used by 367 is a placeholder. How many
  SKUs is too many is a judgement call, so it is a flag
  (``--max-skus-per-hash``) rather than a constant.

Every distinct image is written to the manifest regardless, carrying
``n_skus_sharing`` as a column. The cutoff is applied later at index-build
time, so re-tuning it costs nothing instead of another GPU pass.

Also splits SKUs into tuning/test sets and freezes a fixed query set. Both are
cheap now and expensive later: every threshold chosen by inspecting the same
data it is reported against is a threshold that means nothing, and without a
frozen query set a regression between build A and build B is undetectable.

Read-only over the image tree. Writes only into ``<dataset-dir>/index_build/``.

Run:
    python scripts/rigidhitch_dedup_images.py --images-dir "C:\\path\\to\\images_clean"
    python scripts/rigidhitch_dedup_images.py --images-dir "..." --max-skus-per-hash 2
"""

import argparse
import hashlib
import json
import random
import re
from collections import Counter, defaultdict
from pathlib import Path

IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".webp"}
DEFAULT_IMAGES_DIR = Path(
    r"C:\Users\Vasuki.KLIZER-49\Downloads\images_clean\images_clean"
)
DEFAULT_OUT_DIR = Path(
    r"C:\Users\Vasuki.KLIZER-49\Downloads\rigidhitch_dataset\rigidhitch_dataset\index_build"
)
# Fixed so the split and the query set are reproducible across machines and runs.
SPLIT_SEED = 20260827
TEST_FRACTION = 0.20
QUERY_SET_SIZE = 300
READ_CHUNK = 1 << 20


def file_digest(path: Path) -> str:
    """SHA-256 of a file's bytes, read in chunks so large files don't sit in RAM."""
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(READ_CHUNK), b""):
            digest.update(chunk)
    return digest.hexdigest()


def scan(images_dir: Path) -> tuple[dict[str, list[str]], int]:
    """Hash every image under ``images_dir``.

    Returns:
        A ``{sha256: [<sku>/<file>, ...]}`` map and the total file count. The
        path list preserves every occurrence, so a hash appearing under three
        SKUs has three entries.
    """
    by_hash: dict[str, list[str]] = defaultdict(list)
    total = 0

    for sku_dir in sorted(d for d in images_dir.iterdir() if d.is_dir()):
        for image in sorted(sku_dir.iterdir()):
            if image.suffix.lower() not in IMAGE_EXTS:
                continue
            by_hash[file_digest(image)].append(f"{sku_dir.name}/{image.name}")
            total += 1
            if total % 5000 == 0:
                print(f"  hashed {total:,}...", flush=True)

    return by_hash, total


def build_rows(by_hash: dict[str, list[str]]) -> list[dict]:
    """One manifest row per distinct image, keeping the first path for each hash.

    A hash shared across SKUs is genuinely ambiguous - there is no correct SKU
    to attribute it to - so it is recorded once under its first-seen SKU with
    ``n_skus_sharing`` set. The index build is what decides whether to use it,
    and at the default cutoff of 1 it never will.
    """
    rows: list[dict] = []
    for digest, paths in sorted(by_hash.items(), key=lambda kv: kv[1][0]):
        skus = sorted({p.split("/", 1)[0] for p in paths})
        rows.append({
            "sku": paths[0].split("/", 1)[0],
            "rel": paths[0],
            "sha256": digest,
            "n_skus_sharing": len(skus),
            "n_copies": len(paths),
            # Who shares it, not just how many. The count alone cannot tell a
            # placeholder used by 367 unrelated products from a photo shared by
            # one part's bundle variants - see is_variant_family().
            "sharers": skus,
        })
    return rows


def variant_root(sku: str) -> str:
    """The base SKU a bundle variant belongs to.

    RigidHitch sells one part under several SKUs - ``BX2619`` is the baseplate,
    ``BX2619-20`` / ``-70`` / ``-80`` are the same baseplate packed with
    different extras. They legitimately share one photograph.
    """
    return re.sub(r"-\d{1,3}$", "", sku)


def is_variant_family(skus: list[str]) -> bool:
    """True when every SKU sharing a photo is a bundle of the same part.

    This is the distinction the raw share-count cannot make, and getting it
    wrong is expensive in both directions:

    * One photo used by 367 unrelated products is a placeholder. Keeping it
      would let a single image answer for 367 SKUs - worse than useless.
    * One photo used by ``BX2619`` and its three bundles is a perfectly good
      picture of a real part. Discarding it makes that part unfindable, which
      is exactly what happened: 1,322 products were dropped for this reason.
    """
    return len({variant_root(sku) for sku in skus}) == 1


def load_sharers(build_dir: Path) -> dict[str, list[str]]:
    """The sha256 -> sharing-SKUs sidecar, or empty when absent.

    A sidecar rather than a column on ``embed_rows.jsonl``, because that file's
    hash is recorded at embed time and checked before every build: row N of the
    vector array must be line N of the manifest, so editing it - even to add a
    field, even preserving order - trips the guard that protects against
    silently misattributing every vector.
    """
    path = build_dir / "hash_sharers.json"
    return json.loads(path.read_text(encoding="utf-8")) if path.is_file() else {}


def keeps_row(
    row: dict,
    max_skus_per_hash: int,
    allow_families: bool,
    sharers: dict[str, list[str]] | None = None,
) -> bool:
    """Whether an image survives the cross-SKU filter.

    Falls back to the strict count when the sharer list is unavailable: without
    knowing *who* shares a photo the family test cannot run, and guessing would
    risk keeping a placeholder used by hundreds of unrelated products.
    """
    if row["n_skus_sharing"] <= max_skus_per_hash:
        return True
    if not allow_families:
        return False
    shared_with = (sharers or {}).get(row["sha256"]) or row.get("sharers")
    return bool(shared_with and is_variant_family(shared_with))


def surviving_counts(
    rows: list[dict], max_skus_per_hash: int, allow_families: bool = False
) -> Counter:
    """Images each SKU keeps once the cross-SKU cutoff is applied."""
    counts: Counter = Counter()
    for row in rows:
        if keeps_row(row, max_skus_per_hash, allow_families):
            counts[row["sku"]] += 1
    return counts


def split_skus(skus: list[str]) -> tuple[list[str], list[str]]:
    """Deterministic tuning/test split, seeded so every machine agrees."""
    shuffled = sorted(skus)
    random.Random(SPLIT_SEED).shuffle(shuffled)
    cut = int(len(shuffled) * (1 - TEST_FRACTION))
    return sorted(shuffled[:cut]), sorted(shuffled[cut:])


def main() -> None:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument(
        "--images-dir",
        type=Path,
        default=DEFAULT_IMAGES_DIR,
        help=f"Root holding one folder per SKU (default: {DEFAULT_IMAGES_DIR})",
    )
    parser.add_argument(
        "--out-dir",
        type=Path,
        default=DEFAULT_OUT_DIR,
        help=f"Where manifests are written (default: {DEFAULT_OUT_DIR})",
    )
    parser.add_argument(
        "--max-skus-per-hash",
        type=int,
        default=1,
        help="Keep an image only if its content is used by at most this many SKUs. "
             "1 (default) drops every cross-SKU shared image. Reported only - the "
             "cutoff is applied at index-build time, so this does not change what "
             "gets embedded.",
    )
    args = parser.parse_args()

    if not args.images_dir.is_dir():
        raise SystemExit(f"images dir not found: {args.images_dir}")

    print(f"Hashing images under {args.images_dir}")
    by_hash, total = scan(args.images_dir)
    rows = build_rows(by_hash)

    unique = len(rows)
    duplicates = total - unique
    cross_sku = {d: sorted({p.split("/", 1)[0] for p in ps})
                 for d, ps in by_hash.items()
                 if len({p.split("/", 1)[0] for p in ps}) > 1}

    all_skus = sorted({d.name for d in args.images_dir.iterdir() if d.is_dir()})
    kept = surviving_counts(rows, args.max_skus_per_hash)
    emptied = sorted(s for s in all_skus if kept.get(s, 0) == 0)
    with_images = sorted(s for s in all_skus if kept.get(s, 0) > 0)

    tuning, test = split_skus(with_images)
    # Query set is drawn from the test half only, and from SKUs with enough
    # photos to be scored by leave-one-out at all.
    eligible = [s for s in test if kept.get(s, 0) >= 3]
    query_set = sorted(
        random.Random(SPLIT_SEED + 1).sample(eligible, min(QUERY_SET_SIZE, len(eligible)))
    )

    args.out_dir.mkdir(parents=True, exist_ok=True)

    rows_path = args.out_dir / "embed_rows.jsonl"
    with rows_path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row) + "\n")

    dist = Counter(kept.get(s, 0) for s in all_skus)
    manifest = {
        "images_dir": str(args.images_dir),
        "total_files": total,
        "unique_by_content": unique,
        "duplicate_files": duplicates,
        "cross_sku_hashes": len(cross_sku),
        "max_skus_sharing_one_hash": max((len(v) for v in cross_sku.values()), default=0),
        "max_skus_per_hash_reported": args.max_skus_per_hash,
        "skus_total": len(all_skus),
        "skus_with_images": len(with_images),
        "skus_without_images": emptied,
        "photos_per_sku_after": {str(k): v for k, v in sorted(dist.items())},
        "shared_hash_skus": {d: skus for d, skus in sorted(cross_sku.items())},
    }
    (args.out_dir / "manifest.dedup.json").write_text(json.dumps(manifest, indent=2))

    (args.out_dir / "split.json").write_text(json.dumps({
        "seed": SPLIT_SEED,
        "test_fraction": TEST_FRACTION,
        "tuning_skus": tuning,
        "test_skus": test,
        "frozen_query_skus": query_set,
    }, indent=2))

    surviving = sum(kept.values())
    print()
    print("=" * 58)
    print(f"Files on disk            : {total:,}")
    print(f"Distinct by content      : {unique:,}   <- embedded")
    print(f"Byte-identical duplicates: {duplicates:,} ({duplicates / total * 100:.1f}%)")
    print(f"Hashes shared >1 SKU     : {len(cross_sku):,}"
          f"  (worst: one image across {manifest['max_skus_sharing_one_hash']} SKUs)")
    print()
    print(f"At --max-skus-per-hash {args.max_skus_per_hash}:")
    print(f"  images kept            : {surviving:,}")
    print(f"  SKUs with images       : {len(with_images):,} of {len(all_skus):,}")
    print(f"  SKUs left with none    : {len(emptied):,} "
          f"({len(emptied) / len(all_skus) * 100:.1f}%)")
    print()
    print(f"Split: {len(tuning):,} tuning / {len(test):,} test"
          f"   frozen query set: {len(query_set):,} SKUs")
    print(f"\nWrote {rows_path.name}, manifest.dedup.json, split.json -> {args.out_dir}")


if __name__ == "__main__":
    main()
