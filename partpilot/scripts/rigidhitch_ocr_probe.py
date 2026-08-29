"""How much usable text is actually printed on RigidHitch's parts?

nyris's published pipeline reads part numbers and brand names off the
photograph with OCR and combines them with the visual match. That is the one
signal proven to separate parts a photograph cannot: an unstocked ball mount
looks identical to a stocked one, but the brand stamped on it does not.

Before building that, this measures whether the text is there to read. The
answer decides whether OCR is the cheapest large win available or a week spent
on nothing, and it is cheap to find out.

Text is only counted as *useful* when it matches something we could search on -
the SKU, the manufacturer part number, or the brand. Text in general is common
and near-worthless: "MADE IN USA", warning labels, a rusted logo. Matching is
loose (case-folded, non-alphanumerics stripped) because OCR misreads characters
and an exact-match test would score good reads as failures.

Run:
    python scripts/rigidhitch_ocr_probe.py --skus 10
"""

import argparse
import asyncio
import os
import random
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

DEFAULT_IMAGES = Path(r"C:\Users\Vasuki.KLIZER-49\Downloads\images_clean\images_clean")
# Below this OCR confidence a detection is usually noise - texture, a shadow
# edge, or a reflection read as a character.
MIN_CONFIDENCE = 0.5


def normalise(text: str) -> str:
    """Case-fold and strip punctuation, so 'BX-2619' and 'bx2619' compare equal."""
    return re.sub(r"[^a-z0-9]", "", text.lower())


def printable(text: str) -> str:
    """Drop characters the Windows console cannot encode.

    The recognition model is multilingual and occasionally reads a CJK glyph out
    of a texture or a reflection. Printing one raises UnicodeEncodeError under
    cp1252 and kills the run - losing the whole sample over a character that was
    never really there.
    """
    return text.encode("ascii", "replace").decode("ascii")


async def load_products(skus: list[str]) -> dict[str, dict]:
    from dotenv import load_dotenv

    load_dotenv()
    import sqlalchemy as sa
    from sqlalchemy.ext.asyncio import create_async_engine

    url = os.environ["RIGIDHITCH_DATABASE_URL"].replace("postgresql://", "postgresql+asyncpg://")
    engine = create_async_engine(url)
    try:
        async with engine.connect() as conn:
            rows = (await conn.execute(
                sa.text("select sku, brand, product_name, manufacturer_part_number "
                        "from products where sku = any(:skus)"),
                {"skus": skus},
            )).mappings().all()
            return {r["sku"]: dict(r) for r in rows}
    finally:
        await engine.dispose()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--images", type=Path, default=DEFAULT_IMAGES)
    parser.add_argument("--skus", type=int, default=10)
    parser.add_argument("--seed", type=int, default=20260829,
                        help="Fixed so the sample is reproducible and not cherry-picked.")
    args = parser.parse_args()

    from rapidocr_onnxruntime import RapidOCR

    folders = sorted(d for d in args.images.iterdir() if d.is_dir())
    chosen = random.Random(args.seed).sample(folders, min(args.skus, len(folders)))
    products = asyncio.run(load_products([d.name for d in chosen]))

    ocr = RapidOCR()
    useful = 0
    any_text = 0

    for folder in chosen:
        sku = folder.name
        product = products.get(sku, {})
        photos = sorted(p for p in folder.iterdir() if p.suffix.lower() in {".jpg", ".jpeg", ".png"})

        # What a search could actually use, if OCR found it.
        targets = {
            "SKU": sku,
            "MPN": product.get("manufacturer_part_number") or "",
            "brand": product.get("brand") or "",
        }
        targets = {k: v for k, v in targets.items() if v and v != "Unknown"}

        found: list[str] = []
        for photo in photos:
            result, _ = ocr(str(photo))
            for entry in result or []:
                text, confidence = entry[1], float(entry[2])
                if confidence >= MIN_CONFIDENCE and text.strip():
                    found.append(text.strip())

        blob = normalise(" ".join(found))
        hits = [name for name, value in targets.items()
                if len(normalise(value)) >= 3 and normalise(value) in blob]

        name = printable((product.get("product_name") or "")[:52])
        print(f"\n{sku}  ({len(photos)} photo{'s' if len(photos) != 1 else ''})  {name}")
        print(f"  brand: {product.get('brand') or '-'}   MPN: {product.get('manufacturer_part_number') or '-'}")
        if found:
            any_text += 1
            shown = ", ".join(dict.fromkeys(found))[:150]
            print(f"  text read : {printable(shown)}")
        else:
            print("  text read : (none)")
        print(f"  USEFUL    : {'yes -> ' + ', '.join(hits) if hits else 'no'}")
        if hits:
            useful += 1

    total = len(chosen)
    print()
    print("=" * 68)
    print(f"{any_text}/{total} products had any readable text")
    print(f"{useful}/{total} had text matching their own SKU, part number or brand")
    print()
    print("Only the second number matters. Text a search cannot look up - warning")
    print("labels, 'MADE IN USA', a brand we cannot tie to a product - does not")
    print("help identify anything.")


if __name__ == "__main__":
    main()
