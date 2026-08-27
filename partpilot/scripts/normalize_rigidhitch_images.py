"""Phase 2: normalize RigidHitch's catalog images for training.

Two passes over the corpus, driven by an evidence-based scan rather than an
assumption: a background-color check (corner-pixel whiteness) flags which
images actually need cleanup, instead of guessing from a brand prefix or a
small sample. On the full 27,297-image corpus this found 4,203 flagged images
across 2,153 SKUs (19.9%) - notably more than a "Blue Ox line only" guess
would have caught, since a handful of non-standard photos exist scattered
across other brands too.

Flagged images go through rembg (background removal, composited back onto a
white canvas - rembg's raw output is transparent, and JPG has no alpha
channel). Every image, flagged or not, is squashed to a consistent square
size on the way out - the same "squash, don't pad" convention PartPilot's own
Brain 1 checkpoint was trained on (CLASSIFIER_PAD_TO_SQUARE=False).

Output goes to a separate images_clean/ tree; originals are never modified.
A low_confidence_skus.json manifest lists every SKU with at least one flagged
image, for Phase 5 to slice accuracy on separately.

Run:
    python scripts/normalize_rigidhitch_images.py
    python scripts/normalize_rigidhitch_images.py --limit 50   # smoke test
"""

import argparse
import json
import time
from pathlib import Path

from PIL import Image
from rembg import new_session, remove

DEFAULT_DATASET_DIR = Path(r"C:\Users\Vinith\Downloads\rigidhitch_dataset\rigidhitch_dataset")
WHITENESS_THRESHOLD = 235
TARGET_SIZE = 1000


def scan_whiteness(dataset_dir: Path) -> tuple[list[str], set[str]]:
    """Corner-pixel check across every image; returns (flagged image paths, flagged SKUs).

    Paths are relative to dataset_dir (e.g. "images/01090/01090-3.jpg").
    """
    images_dir = dataset_dir / "images"
    flagged_images: list[str] = []
    flagged_skus: set[str] = set()

    for sku_dir in sorted(d for d in images_dir.iterdir() if d.is_dir()):
        for img_path in sku_dir.glob("*.jpg"):
            im = Image.open(img_path).convert("RGB")
            w, h = im.size
            corners = [im.getpixel((2, 2)), im.getpixel((w - 3, 2)), im.getpixel((2, h - 3)), im.getpixel((w - 3, h - 3))]
            avg = tuple(sum(c[k] for c in corners) / 4 for k in range(3))
            if not all(v > WHITENESS_THRESHOLD for v in avg):
                flagged_images.append(str(img_path.relative_to(dataset_dir)).replace("\\", "/"))
                flagged_skus.add(sku_dir.name)

    return flagged_images, flagged_skus


def load_or_scan(dataset_dir: Path, cache_path: Path) -> tuple[set[str], set[str]]:
    if cache_path.is_file():
        data = json.loads(cache_path.read_text())
        # Normalize separators: an earlier ad-hoc scan cached backslash paths
        # on Windows, but every runtime comparison below uses forward slashes.
        flagged_images = {p.replace("\\", "/") for p in data["flagged_images"]}
        return flagged_images, set(data["flagged_skus"])

    print("No cached scan found - running full-corpus whiteness scan...")
    flagged_images, flagged_skus = scan_whiteness(dataset_dir)
    cache_path.write_text(json.dumps({
        "flagged_images": sorted(flagged_images),
        "flagged_skus": sorted(flagged_skus),
    }, indent=2))
    return set(flagged_images), flagged_skus


def clean_and_resize(im: Image.Image, session, target_size: int) -> Image.Image:
    """Remove the background (composited onto white) and squash to target_size."""
    removed = remove(im.convert("RGB"), session=session)  # RGBA, transparent bg
    canvas = Image.new("RGB", removed.size, (255, 255, 255))
    canvas.paste(removed, mask=removed.split()[3])
    return canvas.resize((target_size, target_size), Image.LANCZOS)


def resize_only(im: Image.Image, target_size: int) -> Image.Image:
    return im.convert("RGB").resize((target_size, target_size), Image.LANCZOS)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--dataset-dir", type=Path, default=DEFAULT_DATASET_DIR)
    parser.add_argument("--output-dir", type=Path, default=None, help="Default: <dataset-dir>/images_clean")
    parser.add_argument("--scan-cache", type=Path, default=Path(__file__).parent / "_whiteness_scan.json")
    parser.add_argument("--target-size", type=int, default=TARGET_SIZE)
    parser.add_argument("--limit", type=int, default=None, help="Process only the first N SKU folders (smoke test).")
    args = parser.parse_args()

    output_dir = args.output_dir or (args.dataset_dir / "images_clean")
    images_dir = args.dataset_dir / "images"

    flagged_images, flagged_skus = load_or_scan(args.dataset_dir, args.scan_cache)
    print(f"Flagged images: {len(flagged_images)}  |  flagged SKUs: {len(flagged_skus)}")

    manifest_path = args.dataset_dir / "low_confidence_skus.json"
    manifest_path.write_text(json.dumps({
        "reason": "at least one catalog photo failed the corner-whiteness check "
                  "(non-studio background, e.g. installed-on-vehicle shots)",
        "threshold": WHITENESS_THRESHOLD,
        "sku_count": len(flagged_skus),
        "skus": sorted(flagged_skus),
    }, indent=2))
    print(f"Wrote manifest: {manifest_path} ({len(flagged_skus)} SKUs)")

    session = new_session("u2net")
    sku_dirs = sorted(d for d in images_dir.iterdir() if d.is_dir())
    if args.limit:
        sku_dirs = sku_dirs[: args.limit]

    t0 = time.time()
    n_total = n_cleaned = n_resized_only = n_errors = 0
    for i, sku_dir in enumerate(sku_dirs):
        out_dir = output_dir / sku_dir.name
        out_dir.mkdir(parents=True, exist_ok=True)
        for img_path in sku_dir.glob("*.jpg"):
            rel = str(img_path.relative_to(args.dataset_dir)).replace("\\", "/")
            n_total += 1
            try:
                im = Image.open(img_path)
                if rel in flagged_images:
                    out = clean_and_resize(im, session, args.target_size)
                    n_cleaned += 1
                else:
                    out = resize_only(im, args.target_size)
                    n_resized_only += 1
                out.save(out_dir / img_path.name, "JPEG", quality=92)
            except Exception as exc:  # noqa: BLE001
                n_errors += 1
                print(f"  [error] {rel}: {type(exc).__name__}: {exc}")

        if i % 500 == 0 or i == len(sku_dirs) - 1:
            elapsed = time.time() - t0
            print(f"  {i + 1}/{len(sku_dirs)} SKUs | {n_total} images ({n_cleaned} cleaned, {n_resized_only} resized-only) | {elapsed:.0f}s elapsed")

    print(f"\nDone in {time.time() - t0:.0f}s")
    print(f"  {n_total} images total, {n_cleaned} background-cleaned, {n_resized_only} resized only, {n_errors} errors")
    print(f"  Output: {output_dir}")


if __name__ == "__main__":
    main()
