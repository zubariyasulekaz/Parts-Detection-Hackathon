"""Clean the two real data-quality issues found in RigidHitch's catalog.csv.

A full column-by-column audit (duplicate SKUs, missing required fields,
category/brand consistency, image_count vs. files on disk, attributes JSON
validity) came back clean except for two things:

1. 24 rows have raw HTML left in `description` from a scrape (e.g. `<p>` tags,
   `&trade;` entities) instead of plain text.
2. 586 rows (5.4%) have a blank `brand`.

Nothing else is touched - the category column, image_count, and attributes
JSON are all already correct and are copied through unchanged. Never
overwrites the original catalog.csv; always writes a new file alongside it.

Run:
    python scripts/clean_rigidhitch_catalog.py --dataset-dir "C:\\path\\to\\rigidhitch_dataset"
"""

import argparse
import csv
import html
import re
from pathlib import Path

DEFAULT_DATASET_DIR = Path(r"C:\Users\Vinith\Downloads\rigidhitch_dataset\rigidhitch_dataset")
UNKNOWN_BRAND = "Unknown"

# Requires a letter (optionally after `/`) right after `<`, and forbids another
# `<` before the closing `>` - so a real tag like `<span style="...">` matches,
# but a comparison like `Low (<120v) / High (>132v)` does not (no letter after
# `<`, and it would otherwise span across unrelated text to the next `>`).
TAG_RE = re.compile(r"</?[a-zA-Z][^<>]*>")
ENTITY_RE = re.compile(r"&[a-zA-Z#][a-zA-Z0-9#]{1,8};")


def has_html(value: str) -> bool:
    """True if `value` contains an actual HTML tag or entity (not just stray whitespace)."""
    return bool(TAG_RE.search(value) or ENTITY_RE.search(value))


def clean_description(value: str) -> str:
    """Strip HTML tags and decode HTML entities, collapsing extra whitespace left behind."""
    if not value:
        return value
    without_tags = TAG_RE.sub(" ", value)
    decoded = html.unescape(without_tags)
    return re.sub(r"\s+", " ", decoded).strip()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument(
        "--dataset-dir",
        type=Path,
        default=DEFAULT_DATASET_DIR,
        help=f"Root folder containing catalog.csv (default: {DEFAULT_DATASET_DIR})",
    )
    args = parser.parse_args()

    csv_path = args.dataset_dir / "catalog.csv"
    if not csv_path.is_file():
        raise SystemExit(f"catalog.csv not found: {csv_path}")

    with csv_path.open(newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        fieldnames = reader.fieldnames
        rows = list(reader)

    html_fixed = 0
    whitespace_only = 0
    brand_filled = 0
    for row in rows:
        original = row["description"]
        cleaned = clean_description(original)
        if cleaned != original:
            if has_html(original):
                html_fixed += 1
            else:
                whitespace_only += 1
            row["description"] = cleaned

        if not row["brand"].strip():
            row["brand"] = UNKNOWN_BRAND
            brand_filled += 1

    out_path = args.dataset_dir / "catalog.clean.csv"
    with out_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    print(f"Read {len(rows)} rows from {csv_path}")
    print(f"  Removed actual HTML tags/entities from description: {html_fixed} rows")
    print(f"  Trimmed stray whitespace only (no HTML involved): {whitespace_only} rows")
    print(f"  Filled blank brand with '{UNKNOWN_BRAND}': {brand_filled} rows")
    print(f"Wrote {out_path} (original catalog.csv left untouched)")


if __name__ == "__main__":
    main()
