"""Pack the de-duplicated images into one small zip for upload to Colab.

Two savings, both worth having before a 17k-image upload:

* **Only the images in the row manifest.** The corpus holds 27,297 files but
  only 17,103 distinct pictures; the rest are byte-identical copies that would
  embed to the same vector.
* **Downscaled to ``--size`` (default 518px).** DINOv2 resizes to a few hundred
  pixels internally, so shipping 1000px originals uploads bytes the model
  immediately throws away. Together these take the upload from ~1.8 GB to
  roughly 250 MB.

One zip, not a folder: uploading 17k individual files to Drive is dominated by
per-file overhead and fails far more often than a single large transfer.

Paths inside the zip match ``rel`` in the manifest exactly (``<sku>/<file>``),
so the embedding script resolves them unchanged after extraction.

Run:
    python scripts/rigidhitch_pack_for_colab.py
    python scripts/rigidhitch_pack_for_colab.py --size 518 --quality 92
"""

import argparse
import io
import json
import zipfile
from pathlib import Path

from PIL import Image

DEFAULT_IMAGES_DIR = Path(
    r"C:\Users\Vasuki.KLIZER-49\Downloads\images_clean\images_clean"
)
DEFAULT_BUILD_DIR = Path(
    r"C:\Users\Vasuki.KLIZER-49\Downloads\rigidhitch_dataset\rigidhitch_dataset\index_build"
)


def load_rows(path: Path) -> list[dict]:
    if not path.is_file():
        raise SystemExit(
            f"row manifest not found: {path}\nRun scripts/rigidhitch_dedup_images.py first."
        )
    with path.open(encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]


def downscale(image: Image.Image, size: int) -> Image.Image:
    """Shrink so the longest edge is ``size``, preserving aspect ratio.

    Never upscales - a source smaller than ``size`` is left alone rather than
    interpolated up to a bigger file with no more detail in it.
    """
    if max(image.size) <= size:
        return image
    scale = size / max(image.size)
    new_size = (max(1, round(image.width * scale)), max(1, round(image.height * scale)))
    return image.resize(new_size, Image.LANCZOS)


def main() -> None:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--images-dir", type=Path, default=DEFAULT_IMAGES_DIR)
    parser.add_argument("--build-dir", type=Path, default=DEFAULT_BUILD_DIR)
    parser.add_argument("--out", type=Path, default=None,
                        help="Zip path (default: <build-dir>/rigidhitch_images_<size>.zip)")
    parser.add_argument("--size", type=int, default=518,
                        help="Longest edge in pixels (default: 518)")
    parser.add_argument("--quality", type=int, default=92,
                        help="JPEG quality (default: 92)")
    args = parser.parse_args()

    rows = load_rows(args.build_dir / "embed_rows.jsonl")
    out_path = args.out or args.build_dir / f"rigidhitch_images_{args.size}.zip"
    out_path.parent.mkdir(parents=True, exist_ok=True)

    written = 0
    skipped = 0
    source_bytes = 0

    with zipfile.ZipFile(out_path, "w", zipfile.ZIP_STORED) as archive:
        # ZIP_STORED, not DEFLATE: JPEG is already compressed, so deflating it
        # costs CPU on every file and saves almost nothing.
        for row in rows:
            source = args.images_dir / row["rel"]
            try:
                source_bytes += source.stat().st_size
                with Image.open(source) as handle:
                    image = downscale(handle.convert("RGB"), args.size)
                    buffer = io.BytesIO()
                    image.save(buffer, "JPEG", quality=args.quality, optimize=True)
                archive.writestr(row["rel"], buffer.getvalue())
                written += 1
            except Exception as exc:  # noqa: BLE001
                print(f"  [skip] {row['rel']}: {type(exc).__name__}: {exc}")
                skipped += 1

            if written % 2000 == 0 and written:
                print(f"  packed {written:,}/{len(rows):,}...", flush=True)

    packed_mb = out_path.stat().st_size / (1 << 20)
    source_mb = source_bytes / (1 << 20)
    print()
    print(f"Packed {written:,} images at {args.size}px  ({skipped} skipped)")
    print(f"  source  : {source_mb:,.0f} MB")
    print(f"  zip     : {packed_mb:,.0f} MB  ({packed_mb / source_mb * 100:.0f}% of source)")
    print(f"Wrote {out_path}")
    print("\nUpload this single file to Drive, then unzip it to /content inside Colab.")


if __name__ == "__main__":
    main()
