"""Load datasets/catalog.csv into the products table.

Brain 3 reads product details from the database, but nothing ever put them
there, so the app could identify a SKU and then find nothing to show for it.
This fills the gap.

Safe to re-run: rows are upserted on sku, so editing the CSV and running again
updates the existing products rather than failing on duplicate keys.

Two shape changes happen on the way in, because the CSV is flat and the table
is not:

  compatible_vehicles   "Toyota RAV4 (2019-2023)" becomes one {make, model,
                        year} object per year in the range, since that is what
                        ProductBase expects. Entries with no year in them
                        ("Universal Fitment") are dropped and reported - they
                        do not fit the make/model/year shape.

  image_paths           filled from the files actually on disk rather than the
                        CSV's image_folder, so the stored list reflects reality.

  attributes            a JSON string in the CSV, stored as JSONB. Written by
                        scripts/extract_product_attributes.py; a blank or
                        unparseable cell imports as {} rather than failing the
                        run, since the attributes are an enrichment and not
                        something the catalog is broken without.

Run:
    python scripts/import_catalog_to_db.py
    python scripts/import_catalog_to_db.py --dry-run   # parse and report only
"""

import argparse
import asyncio
import csv
import json
import os
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy.dialects.postgresql import insert  # noqa: E402

from backend.config.paths import CATALOG_CSV_PATH, DATASETS_DIR  # noqa: E402
from backend.config.settings import get_settings  # noqa: E402
from backend.core.database import engine  # noqa: E402
from backend.pipeline.brain3_catalog.models import Product  # noqa: E402

IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".webp"}
#: "Toyota RAV4 (2019-2023)" -> name, first year, last year
VEHICLE_RE = re.compile(r"^(.*?)\s*\((\d{4})\s*[-–]\s*(\d{4})\)")
#: "Honda Civic (2018)" - single year rather than a range
VEHICLE_ONE_YEAR_RE = re.compile(r"^(.*?)\s*\((\d{4})\)")


def split_list(value: str) -> list[str]:
    """Split a pipe-separated cell into a clean list."""
    return [part.strip() for part in (value or "").split("|") if part.strip()]


def parse_attributes(value: str, sku: str) -> dict:
    """Read the `attributes` JSON cell, tolerating a blank or malformed one.

    The attributes enrich matching; a bad cell should cost that one product its
    extras, not abort an import of the whole catalog.
    """
    text = (value or "").strip()
    if not text:
        return {}
    try:
        parsed = json.loads(text)
    except json.JSONDecodeError:
        print(f"  [warn] {sku}: attributes cell is not valid JSON; importing as {{}}")
        return {}
    if not isinstance(parsed, dict):
        print(f"  [warn] {sku}: attributes is {type(parsed).__name__}, expected object; importing as {{}}")
        return {}
    return parsed


def parse_vehicles(value: str) -> tuple[list[dict], list[str]]:
    """Expand pipe-separated vehicle strings into {make, model, year} objects.

    A year range produces one entry per year, since the schema stores a single
    year per entry. Returns the parsed entries plus anything that could not be
    parsed, so the caller can report it rather than silently dropping it.
    """
    parsed: list[dict] = []
    skipped: list[str] = []

    for entry in split_list(value):
        match = VEHICLE_RE.match(entry)
        if match:
            name, first, last = match.group(1), int(match.group(2)), int(match.group(3))
            years = range(first, last + 1)
        else:
            match = VEHICLE_ONE_YEAR_RE.match(entry)
            if not match:
                skipped.append(entry)
                continue
            name, years = match.group(1), [int(match.group(2))]

        # "Toyota RAV4" -> make "Toyota", model "RAV4". Single-word entries
        # keep the whole string as the model so `make` is never empty.
        words = name.strip().split()
        make = words[0] if len(words) > 1 else name.strip()
        model = " ".join(words[1:]) if len(words) > 1 else name.strip()
        for year in years:
            parsed.append({"make": make, "model": model, "year": year})

    return parsed, skipped


def image_paths_for(sku: str, image_folder: str) -> list[str]:
    """Paths of the images actually present for this SKU, relative to datasets/."""
    folder = DATASETS_DIR / (image_folder or f"images/{sku}")
    if not folder.is_dir():
        return []
    return sorted(
        f"{image_folder}/{f.name}"
        for f in folder.iterdir()
        if f.suffix.lower() in IMAGE_EXTS
    )


def build_rows() -> tuple[list[dict], list[tuple[str, str]]]:
    """Read the CSV into product rows ready for insert."""
    if not CATALOG_CSV_PATH.is_file():
        raise SystemExit(f"catalog.csv not found: {CATALOG_CSV_PATH}")

    rows: list[dict] = []
    unparsed: list[tuple[str, str]] = []

    with CATALOG_CSV_PATH.open(newline="", encoding="utf-8-sig") as f:
        for record in csv.DictReader(f):
            sku = (record.get("sku") or "").strip()
            if not sku:
                continue

            vehicles, skipped = parse_vehicles(record.get("compatible_vehicles", ""))
            unparsed += [(sku, entry) for entry in skipped]

            rows.append({
                "sku": sku,
                "product_name": (record.get("product_name") or "").strip() or sku,
                # brand is NOT NULL; fall back to "Unknown" rather than failing
                # the whole import over a blank cell.
                "brand": (record.get("brand") or "").strip() or "Unknown",
                "category": (record.get("category") or "").strip(),
                "description": (record.get("description") or "").strip() or None,
                "manufacturer_part_number": (
                    record.get("manufacturer_part_number") or ""
                ).strip()
                or None,
                "attributes": parse_attributes(record.get("attributes", ""), sku),
                "image_paths": image_paths_for(sku, (record.get("image_folder") or "").strip()),
                "replacement_sku": (record.get("replacement_sku") or "").strip() or None,
                "alternative_skus": split_list(record.get("alternative_sku", "")),
                "accessory_skus": split_list(record.get("accessory_skus", "")),
                "compatible_vehicles": vehicles,
            })

    return rows, unparsed


async def upsert(rows: list[dict]) -> None:
    """Insert the rows, updating any SKU that is already present."""
    statement = insert(Product).values(rows)
    statement = statement.on_conflict_do_update(
        index_elements=[Product.sku],
        set_={
            column: statement.excluded[column]
            for column in (
                "product_name", "brand", "category", "description", "image_paths",
                "manufacturer_part_number", "attributes",
                "replacement_sku", "alternative_skus", "accessory_skus",
                "compatible_vehicles",
            )
        },
    )
    async with engine.begin() as connection:
        await connection.execute(statement)


async def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Parse the CSV and report what would be imported, without writing.",
    )
    args = parser.parse_args()

    rows, unparsed = build_rows()

    print(f"Read {len(rows)} products from {CATALOG_CSV_PATH.name}")
    no_images = [r["sku"] for r in rows if not r["image_paths"]]
    if no_images:
        print(f"  [warn] no images on disk for: {', '.join(no_images)}")
    if unparsed:
        print(f"  [warn] {len(unparsed)} vehicle entries had no year and were dropped:")
        for sku, entry in unparsed:
            print(f"           {sku}: {entry}")

    total_vehicles = sum(len(r["compatible_vehicles"]) for r in rows)
    total_images = sum(len(r["image_paths"]) for r in rows)
    print(f"  {total_images} image paths, {total_vehicles} vehicle-year entries")

    if args.dry_run:
        print("\nDry run - nothing written.")
        example = rows[0]
        print(f"\nExample row ({example['sku']}):")
        for key, value in example.items():
            shown = value if not isinstance(value, list) else f"{value[:2]} ... ({len(value)} items)"
            print(f"  {key:22} {shown}")
        return

    url = get_settings().DATABASE_URL
    # Never print the password.
    print(f"\nWriting to {re.sub(r'://[^@]+@', '://***@', url)}")
    try:
        await upsert(rows)
    except Exception as exc:  # noqa: BLE001
        raise SystemExit(
            f"\nImport failed: {type(exc).__name__}: {exc}\n\n"
            "Check that DATABASE_URL in .env is correct and that the products "
            "table exists (python -m alembic upgrade head)."
        ) from exc
    finally:
        await engine.dispose()

    print(f"Imported {len(rows)} products.")


if __name__ == "__main__":
    asyncio.run(main())
