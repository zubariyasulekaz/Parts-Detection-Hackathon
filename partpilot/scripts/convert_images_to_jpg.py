"""Convert dataset images to JPG so the CLIP pipeline can read them.

Walks ``datasets/images/<SKU>/`` and converts every ``.avif`` / ``.webp``
image to ``.jpg`` (RGB, quality 95). Existing ``.jpg`` files are left alone.

Reading AVIF requires an AVIF-capable Pillow. If a plain ``import PIL`` can't
decode AVIF (as on the default Windows env here), run this in Colab or install
one of:  ``pillow-avif-plugin``  or  ``pillow-heif``.

Run:
    python scripts/convert_images_to_jpg.py                 # convert in place, keep originals
    python scripts/convert_images_to_jpg.py --delete        # convert and delete .avif/.webp
    python scripts/convert_images_to_jpg.py --path some/dir # convert a different folder
"""

import argparse
import os
from pathlib import Path

from PIL import Image

# Best-effort registration of AVIF/HEIF decoders if available.
try:
    import pillow_avif  # noqa: F401  (registers the AVIF plugin on import)
except Exception:
    pass
try:
    import pillow_heif

    pillow_heif.register_heif_opener()
except Exception:
    pass

DEFAULT_PATH = Path(__file__).resolve().parent.parent / "datasets" / "images"
CONVERT_EXTS = {".avif", ".webp"}


def convert_tree(root: Path, delete_originals: bool) -> None:
    converted = 0
    failed = 0

    for sku in sorted(os.listdir(root)):
        sku_path = root / sku
        if not sku_path.is_dir():
            continue

        for file in sorted(os.listdir(sku_path)):
            if Path(file).suffix.lower() not in CONVERT_EXTS:
                continue

            src = sku_path / file
            dst = sku_path / (Path(file).stem + ".jpg")

            try:
                img = Image.open(src).convert("RGB")
                img.save(dst, "JPEG", quality=95)
                converted += 1
                print(f"Converted: {sku}/{file} -> {dst.name}")
                if delete_originals:
                    src.unlink()
            except Exception as exc:  # noqa: BLE001
                failed += 1
                print(f"[FAIL] {sku}/{file}: {type(exc).__name__}: {exc}")

    print(f"\nDone. Converted {converted} file(s), {failed} failure(s).")
    if failed:
        print(
            "Failures usually mean this Pillow can't decode AVIF. "
            "Run in Colab, or install pillow-avif-plugin / pillow-heif."
        )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--path", type=Path, default=DEFAULT_PATH,
                        help="Root folder containing <SKU>/ image subfolders.")
    parser.add_argument("--delete", action="store_true",
                        help="Delete the original .avif/.webp files after converting.")
    args = parser.parse_args()

    if not args.path.exists():
        raise SystemExit(f"Path not found: {args.path}")

    convert_tree(args.path, delete_originals=args.delete)


if __name__ == "__main__":
    main()
