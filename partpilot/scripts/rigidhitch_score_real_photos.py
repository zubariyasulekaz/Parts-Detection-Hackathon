"""Score a folder of real-world photographs against the shipped index.

Every accuracy figure in this project so far compares RigidHitch's catalogue
photographs against RigidHitch's catalogue photographs - white background,
studio lighting, canonical angle. A customer's photograph is none of those, and
published industry benchmarks put the gap at roughly twenty points. Until this
script has been pointed at real photographs, the deployment number is unknown
rather than optimistic.

Runs through the same objects the API request handler builds -
``SimilaritySearchService`` over ``IndexManager`` - so what is measured is what
a customer would get, including background removal, TTA and whitening.

**Naming the files is the whole method.** Put the product's SKU in the filename
and everything else follows:

    02143_amazon_review.jpg
    CM-813748-2.jpeg
    BX88383 ebay used.png

Any token matching a real SKU in the index is taken as the expected answer;
files that name none are still searched and printed, just not scored - so a
folder can hold a mix without curating it first.

Run:
    python scripts/rigidhitch_score_real_photos.py --photos "C:\\path\\to\\real_photos"
"""

import argparse
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from PIL import Image  # noqa: E402

from backend.pipeline.brain2_similarity.index_manager import IndexManager  # noqa: E402
from backend.pipeline.brain2_similarity.search import SimilaritySearchService  # noqa: E402
from backend.utils.image_utils import remove_background  # noqa: E402

DEFAULT_INDEX_DIR = Path(__file__).resolve().parent.parent / "backend" / "models" / "faiss_rigidhitch"
IMAGE_TYPES = {".jpg", ".jpeg", ".png", ".webp", ".bmp"}
# The margin below which the router reports a result as ambiguous. Repeated here
# rather than imported so this script has no dependency on the API layer.
AMBIGUOUS_MARGIN = 0.036


def expected_sku(name: str, known: set[str]) -> str | None:
    """The SKU a filename claims, when it names one the index actually holds.

    Only a token matching a real SKU counts. Filenames are written by hand and
    carry noise - "ebay", "used", "2" - and treating any of that as a part
    number would score the run against products that do not exist.
    """
    for token in re.split(r"[^A-Za-z0-9-]+", Path(name).stem):
        for candidate in (token, token.upper(), token.replace("_", "-").upper()):
            if candidate in known:
                return candidate
    return None


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--photos", type=Path, required=True,
                        help="Folder of real photographs, each named with its SKU.")
    parser.add_argument("--index-dir", type=Path, default=DEFAULT_INDEX_DIR)
    parser.add_argument("--top-k", type=int, default=5)
    parser.add_argument("--no-remove-bg", action="store_true",
                        help="Skip background removal, to measure what it is worth on real photos.")
    args = parser.parse_args()

    if not args.photos.is_dir():
        raise SystemExit(f"not a folder: {args.photos}")

    known = set(json.loads((args.index_dir / "rigidhitch.ids.json").read_text()))
    service = SimilaritySearchService(index_manager=IndexManager(index_dir=args.index_dir))

    photos = sorted(p for p in args.photos.rglob("*") if p.suffix.lower() in IMAGE_TYPES)
    if not photos:
        raise SystemExit(f"no images found under {args.photos}")

    scored = hits1 = hits5 = 0
    flagged_wrong = confident_wrong = 0
    unlabelled: list[str] = []

    print(f"{len(photos)} photo(s), index of {len(known):,} products\n")
    for photo in photos:
        with Image.open(photo) as handle:
            image = handle.convert("RGB")
        query = image if args.no_remove_bg else remove_background(image)
        outcome = service.search(category="rigidhitch", image=query,
                                 top_k=args.top_k, raw_image=image)
        if not outcome.matches:
            print(f"{photo.name[:44]:<46} no results")
            continue

        ranked = [m.sku for m in outcome.matches]
        best = outcome.matches[0].similarity_score
        margin = (best - outcome.matches[1].similarity_score
                  if len(outcome.matches) > 1 else 1.0)
        ambiguous = margin < AMBIGUOUS_MARGIN

        want = expected_sku(photo.name, known)
        if want is None:
            unlabelled.append(photo.name)
            verdict = "not scored"
        else:
            scored += 1
            if ranked[0] == want:
                hits1 += 1
                hits5 += 1
                verdict = "TOP-1"
            elif want in ranked:
                hits5 += 1
                verdict = f"top-{ranked.index(want) + 1}"
            else:
                verdict = "MISS"
            if ranked[0] != want:
                if ambiguous:
                    flagged_wrong += 1
                else:
                    confident_wrong += 1

        print(f"{photo.name[:44]:<46}{verdict:<11}best={best:.3f} margin={margin:.3f}"
              f"{'  ambiguous' if ambiguous else ''}")
        for rank, match in enumerate(outcome.matches, 1):
            mark = " <-- expected" if match.sku == want else ""
            print(f"    {rank}. {match.sku:<20}{match.similarity_score:.3f}{mark}")

    print()
    print("=" * 66)
    if not scored:
        raise SystemExit(
            "No photo named a SKU in the index, so nothing could be scored.\n"
            "Rename each file to include its part number, e.g. 02143_review.jpg"
        )
    print(f"REAL-PHOTO ACCURACY   (n={scored})")
    print("=" * 66)
    print(f"  top-1 : {hits1}/{scored}  ({100 * hits1 / scored:.1f}%)")
    print(f"  top-5 : {hits5}/{scored}  ({100 * hits5 / scored:.1f}%)")
    print()
    print(f"  wrong but flagged ambiguous : {flagged_wrong}")
    print(f"  wrong and looked confident  : {confident_wrong}")
    if unlabelled:
        print(f"\n  {len(unlabelled)} photo(s) named no known SKU and were not scored:")
        for name in unlabelled[:8]:
            print(f"    {name}")
    print()
    print("Compare against 66.5% top-5, measured on catalogue photographs of")
    print("held-out products. A drop here is the real deployment number, and is")
    print("the figure to quote from now on.")
    if scored < 25:
        print(f"\nNote: {scored} photos is a small sample - treat the percentages as")
        print("indicative until there are 30 or more.")


if __name__ == "__main__":
    main()
