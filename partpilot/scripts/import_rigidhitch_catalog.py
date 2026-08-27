"""Create the products table in PartPilot_RigidHitch and import every RigidHitch SKU.

A standalone counterpart to import_catalog_to_db.py: same table shape, same
CSV-parsing rules, but pointed at a separate database and a catalog that
lives outside this repo. Kept separate (rather than reusing
backend.core.database.engine) because that engine is wired to PartPilot's own
DATABASE_URL from .env - this script targets a different database entirely.

The RigidHitch catalog.csv has the identical 13-column header PartPilot's own
catalog.csv uses, with one semantic difference: its `compatible_vehicles`
column holds free-text fitment tags ("2 Inch Receivers", "Fisher Compatible"),
not "Make Model (YYYY-YYYY)" vehicle strings - RigidHitch sells hitches and
towing hardware that fit a hitch class, not a specific car. Forcing those tags
through the {make, model, year} parser used for PartPilot's own data would
silently drop all ~2,039 of them. Instead they land in attributes.fitment,
keeping compatible_vehicles meaning the same thing (vehicle data or empty) in
both databases, and losing no data.

replacement_sku, alternative_skus, accessory_skus, and compatible_vehicles are
dropped entirely from this table (not just left empty) - every row in this
catalog is 0% populated for all four, since RigidHitch's source data has no
replacement/alternative/accessory mapping, and compatible_vehicles' fitment
tags already live in attributes.fitment instead. Re-add them with an ALTER
TABLE if a future data source backfills any of them.

The table itself is owned by `alembic_rigidhitch/` (a parallel migration
environment to the main app's `alembic/`, pointed at this separate database)
rather than created ad hoc by this script - run migrations once before the
first import:

    alembic -c alembic_rigidhitch.ini upgrade head

Safe to re-run: rows are upserted on sku.

Run:
    python scripts/import_rigidhitch_catalog.py --database-url "postgresql://postgres:PASSWORD@localhost/PartPilot_RigidHitch"
    python scripts/import_rigidhitch_catalog.py --database-url "..." --dry-run

The database URL can also be supplied via the RIGIDHITCH_DATABASE_URL
environment variable instead of --database-url (the same variable
`alembic_rigidhitch/env.py` reads), so it never has to be typed into a shell
history or committed anywhere.
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

from dotenv import load_dotenv  # noqa: E402
from sqlalchemy.dialects.postgresql import insert  # noqa: E402
from sqlalchemy.ext.asyncio import create_async_engine  # noqa: E402

from alembic_rigidhitch.schema import products_table  # noqa: E402

# Loads partpilot/.env (if present) so RIGIDHITCH_DATABASE_URL can live there
# like every other setting, rather than needing --database-url every run.
load_dotenv()

IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".webp"}
DEFAULT_DATASET_DIR = Path(r"C:\Users\Vinith\Downloads\rigidhitch_dataset\rigidhitch_dataset")
BATCH_SIZE = 500


def split_list(value: str) -> list[str]:
    """Split a pipe-separated cell into a clean list."""
    return [part.strip() for part in (value or "").split("|") if part.strip()]


def parse_attributes(value: str, sku: str) -> dict:
    """Read the `attributes` JSON cell, tolerating a blank or malformed one."""
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


def image_paths_for(dataset_dir: Path, image_folder: str) -> list[str]:
    """Paths of the images actually present for this SKU, relative to dataset_dir."""
    folder = dataset_dir / (image_folder or "")
    if not image_folder or not folder.is_dir():
        return []
    return sorted(
        f"{image_folder}/{f.name}"
        for f in folder.iterdir()
        if f.suffix.lower() in IMAGE_EXTS
    )


def build_rows(dataset_dir: Path, csv_path: Path) -> list[dict]:
    """Read the CSV into product rows ready for insert."""
    if not csv_path.is_file():
        raise SystemExit(f"catalog.csv not found: {csv_path}")

    rows: list[dict] = []

    with csv_path.open(newline="", encoding="utf-8-sig") as f:
        for record in csv.DictReader(f):
            sku = (record.get("sku") or "").strip()
            if not sku:
                continue

            attributes = parse_attributes(record.get("attributes", ""), sku)
            fitment = (record.get("compatible_vehicles") or "").strip()
            if fitment:
                attributes["fitment"] = fitment

            rows.append({
                "sku": sku,
                "product_name": (record.get("product_name") or "").strip() or sku,
                "brand": (record.get("brand") or "").strip() or "Unknown",
                "category": (record.get("category") or "").strip(),
                "description": (record.get("description") or "").strip() or None,
                "manufacturer_part_number": (
                    record.get("manufacturer_part_number") or ""
                ).strip()
                or None,
                "attributes": attributes,
                "image_paths": image_paths_for(dataset_dir, (record.get("image_folder") or "").strip()),
            })

    return rows


async def upsert(engine, rows: list[dict]) -> None:
    """Insert the rows in batches, updating any SKU that is already present."""
    update_columns = (
        "product_name", "brand", "category", "description", "image_paths",
        "manufacturer_part_number", "attributes",
    )
    async with engine.begin() as connection:
        for start in range(0, len(rows), BATCH_SIZE):
            batch = rows[start:start + BATCH_SIZE]
            statement = insert(products_table).values(batch)
            statement = statement.on_conflict_do_update(
                index_elements=[products_table.c.sku],
                set_={column: statement.excluded[column] for column in update_columns},
            )
            await connection.execute(statement)
            print(f"  ... {min(start + BATCH_SIZE, len(rows))}/{len(rows)}")


def normalize_url(url: str) -> str:
    """Force the asyncpg driver, whatever scheme the caller passed in."""
    if url.startswith("postgresql+asyncpg://"):
        return url
    if url.startswith("postgresql://"):
        return "postgresql+asyncpg://" + url[len("postgresql://"):]
    raise SystemExit(f"Unrecognized database URL scheme: {url.split('://')[0]}://")


async def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument(
        "--database-url",
        default=os.environ.get("RIGIDHITCH_DATABASE_URL"),
        help="postgresql:// connection string for PartPilot_RigidHitch. "
             "Falls back to the RIGIDHITCH_DATABASE_URL env var.",
    )
    parser.add_argument(
        "--dataset-dir",
        type=Path,
        default=DEFAULT_DATASET_DIR,
        help=f"Root folder containing the catalog CSV and images/ (default: {DEFAULT_DATASET_DIR})",
    )
    parser.add_argument(
        "--catalog-file",
        default="catalog.csv",
        help="CSV filename within --dataset-dir (default: catalog.csv). "
             "Use catalog.clean.csv to import the HTML/blank-brand-cleaned version "
             "instead of the raw export - see scripts/clean_rigidhitch_catalog.py.",
    )
    parser.add_argument("--dry-run", action="store_true", help="Parse and report only, write nothing.")
    args = parser.parse_args()

    csv_path = args.dataset_dir / args.catalog_file
    rows = build_rows(args.dataset_dir, csv_path)

    print(f"Read {len(rows)} products from {csv_path}")
    no_images = [r["sku"] for r in rows if not r["image_paths"]]
    if no_images:
        print(f"  [warn] no images on disk for {len(no_images)} SKUs (e.g. {', '.join(no_images[:5])}...)")
    fitment_count = sum(1 for r in rows if "fitment" in r["attributes"])
    total_images = sum(len(r["image_paths"]) for r in rows)
    print(f"  {total_images} image paths, {fitment_count} rows with fitment tags folded into attributes")

    if args.dry_run:
        print("\nDry run - nothing written.")
        example = next(r for r in rows if r["attributes"].get("fitment"))
        print(f"\nExample row with fitment ({example['sku']}):")
        for key, value in example.items():
            shown = value if not isinstance(value, list) else f"{value[:2]} ... ({len(value)} items)"
            print(f"  {key:22} {shown}")
        return

    if not args.database_url:
        raise SystemExit(
            "No database URL given. Pass --database-url or set RIGIDHITCH_DATABASE_URL."
        )
    url = normalize_url(args.database_url)
    engine = create_async_engine(url)
    try:
        print(f"\nConnecting to {re.sub(r'://[^@]+@', '://***@', url)}")
        print(f"Importing {len(rows)} products...")
        await upsert(engine, rows)
    except Exception as exc:  # noqa: BLE001
        raise SystemExit(f"\nImport failed: {type(exc).__name__}: {exc}") from exc
    finally:
        await engine.dispose()

    print(f"\nDone. Imported {len(rows)} products into PartPilot_RigidHitch.")


if __name__ == "__main__":
    asyncio.run(main())
