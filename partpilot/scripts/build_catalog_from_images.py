"""Build the PartPilot dataset from the raw image folders on disk.

Copies images from the source category folders into
``datasets/images/<SKU>/`` and writes ``datasets/catalog.csv`` with one row
per SKU folder found. Deterministic columns (sku, category, part number,
image folder) are filled automatically; manufacturer-curated fields are left
blank for manual completion.

Run:
    python scripts/build_catalog_from_images.py
"""

import csv
import shutil
from pathlib import Path

# --- configuration --------------------------------------------------------
DATASETS_DIR = Path(__file__).resolve().parent.parent / "datasets"
IMAGES_OUT = DATASETS_DIR / "images"
CATALOG_OUT = DATASETS_DIR / "catalog.csv"

# Source folders -> (category label, default product name).
# Each source folder is expected to contain one sub-folder per SKU.
SOURCES = [
    (
        Path.home() / "Downloads" / "BRAKE_PADS",
        "Brake Pads",
        "Disc Brake Pad Set",
    ),
    (
        Path.home() / "Downloads" / "Hackathon_images" / "OIL_FILTERS",
        "Oil Filter",
        "Engine Oil Filter",
    ),
]

IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".webp", ".avif"}

HEADERS = [
    "sku",
    "product_name",
    "brand",
    "category",
    "manufacturer_part_number",
    "compatible_vehicles",   # pipe-separated, e.g. Honda Civic 2016|Toyota Corolla 2018
    "replacement_sku",
    "alternative_sku",
    "accessory_skus",        # pipe-separated SKUs
    "description",
    "image_folder",
    "image_count",
]


def main() -> None:
    rows: list[dict[str, object]] = []
    # Track SKUs per category so we can seed simple demo cross-references.
    by_category: dict[str, list[str]] = {}

    for src_root, category, default_name in SOURCES:
        if not src_root.exists():
            print(f"[skip] source not found: {src_root}")
            continue

        for sku_dir in sorted(p for p in src_root.iterdir() if p.is_dir()):
            sku = sku_dir.name
            images = sorted(
                f for f in sku_dir.iterdir()
                if f.is_file() and f.suffix.lower() in IMAGE_EXTS
            )
            if not images:
                print(f"[skip] no images in {sku_dir}")
                continue

            dest_dir = IMAGES_OUT / sku
            dest_dir.mkdir(parents=True, exist_ok=True)
            for img in images:
                shutil.copy2(img, dest_dir / img.name)

            by_category.setdefault(category, []).append(sku)
            rows.append({
                "sku": sku,
                "product_name": default_name,
                "brand": "",
                "category": category,
                "manufacturer_part_number": sku,
                "compatible_vehicles": "",
                "replacement_sku": "",
                "alternative_sku": "",
                "accessory_skus": "",
                "description": "",
                "image_folder": f"images/{sku}",
                "image_count": len(images),
            })
            print(f"[ok] {sku}: copied {len(images)} images -> {dest_dir}")

    # Seed a simple within-category "alternative" so the recommendation demo
    # has data to show. Each SKU points at the next SKU in its category (ring).
    index = {r["sku"]: r for r in rows}
    for skus in by_category.values():
        if len(skus) < 2:
            continue
        for i, sku in enumerate(skus):
            index[sku]["alternative_sku"] = skus[(i + 1) % len(skus)]

    CATALOG_OUT.parent.mkdir(parents=True, exist_ok=True)
    with CATALOG_OUT.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=HEADERS)
        writer.writeheader()
        writer.writerows(rows)

    print(f"\nWrote {len(rows)} products to {CATALOG_OUT}")
    for cat, skus in by_category.items():
        print(f"  {cat}: {len(skus)} SKUs -> {', '.join(skus)}")


if __name__ == "__main__":
    main()
