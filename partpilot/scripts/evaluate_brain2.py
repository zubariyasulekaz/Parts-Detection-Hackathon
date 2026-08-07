"""Measure Brain 2 (similarity search) retrieval accuracy, leave-one-out.

For every catalog image we ask: "if a customer uploaded THIS photo, would the
system return the right SKU?" To make that honest, the held-out photo is
excluded from its own product's vector pool — otherwise we would be matching
a photo against itself, and accuracy would be a meaningless ~100%.

Method (mirrors ``build_faiss_indexes.py`` + ``FaissIndex.search`` exactly):
  1. Embed every catalog image once (rembg -> vision model), cached in memory.
  2. For each image i of product P, in P's category:
       - every SKU's score = cosine against the L2-normalized centroid of
         that SKU's image vectors (matching ``FaissIndex.search``), with
         image i itself excluded from P's centroid
  3. Record the rank of the correct SKU.

Prefer ``scripts/analyze_index_vectors.py`` when the indexes are already
built — it reads the stored vectors and produces the same numbers in
milliseconds. This script earns its model time only when experimenting with
preprocessing/backends that the indexes don't contain yet.

Products with a single image cannot be queried (nothing left once their only
photo is held out) but still participate as distractors, exactly as their
vectors do in the real index.

Reported metrics:
  Top-1  - correct SKU ranked first        (the headline number)
  Top-3  - correct SKU in the top 3
  MRR    - mean reciprocal rank (1.0 = always first, 0.5 = usually second)

Run:
    python scripts/evaluate_brain2.py               # embed images as-is
    python scripts/evaluate_brain2.py --remove-bg   # match how the index was built
"""

import argparse
import csv
import sys
from collections import defaultdict
from pathlib import Path

import numpy as np
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from backend.config.paths import DATASETS_DIR  # noqa: E402
from backend.pipeline.brain2_similarity.embedding_backends import (  # noqa: E402
    BackendCache,
    backend_for_category,
)
from backend.pipeline.brain2_similarity.embedding_generator import EmbeddingGenerator  # noqa: E402
from backend.utils.image_utils import remove_background  # noqa: E402

IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".webp"}


def load_catalog() -> list[dict[str, str]]:
    """Read catalog.csv directly.

    Brain 3 reads products from the database, but evaluating Brain 2 only
    needs sku/category/image_folder, so we go straight to the CSV and avoid
    requiring a database connection just to score the index.
    """
    path = DATASETS_DIR / "catalog.csv"
    if not path.is_file():
        raise SystemExit(f"catalog.csv not found: {path}")
    with path.open(newline="", encoding="utf-8-sig") as f:
        return [row for row in csv.DictReader(f) if (row.get("sku") or "").strip()]


def unit(v: np.ndarray) -> np.ndarray:
    """L2-normalize a vector (no-op for a zero vector)."""
    n = np.linalg.norm(v)
    return v / n if n else v


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--remove-bg",
        action="store_true",
        help="Background-remove each image first (use this if the index was built with --remove-bg).",
    )
    parser.add_argument(
        "--backend",
        default=None,
        help="Embedding model to score, e.g. dinov2, siglip, 'dinov2+siglip'. "
             "Default: whatever EMBEDDING_BACKEND is set to.",
    )
    args = parser.parse_args()

    records = load_catalog()
    # Without --backend, score each category with the model it is configured to
    # use, which is what the running app will actually do.
    backends = BackendCache()
    generators: dict[str, EmbeddingGenerator] = {}

    def generator_for(category: str) -> EmbeddingGenerator:
        spec = args.backend or backend_for_category(category)
        if spec not in generators:
            generators[spec] = EmbeddingGenerator(backend=backends.get(spec))
        return generators[spec]

    print(f"Embedding backend: {args.backend or 'per-category (see CATEGORY_BACKENDS)'}\n")

    # --- 1. embed every catalog image once -------------------------------
    # category -> sku -> [embedding per image]
    embeddings: dict[str, dict[str, list[np.ndarray]]] = defaultdict(dict)
    total_imgs = 0

    print("Embedding catalog images...")
    for record in records:
        category = (record.get("category") or "").strip()
        sku = record["sku"]
        if not category:
            continue
        folder = DATASETS_DIR / (record.get("image_folder") or f"images/{sku}")
        if not folder.is_dir():
            print(f"  [skip] {sku}: folder not found")
            continue

        generator = generator_for(category)
        vectors: list[np.ndarray] = []
        for img_path in sorted(folder.iterdir()):
            if img_path.suffix.lower() not in IMAGE_EXTS:
                continue
            try:
                with Image.open(img_path) as im:
                    im = im.convert("RGB")
                    if args.remove_bg:
                        im = remove_background(im)
                    vectors.append(unit(np.asarray(generator.generate(im), dtype=np.float32)))
            except Exception as exc:  # noqa: BLE001
                print(f"  [skip] {img_path.name}: {type(exc).__name__}: {exc}")

        if not vectors:
            print(f"  [skip] {sku}: no loadable images")
            continue
        if len(vectors) < 2:
            # Not queryable (nothing left once its only photo is held out),
            # but it still competes as a distractor below.
            print(f"  [distractor-only] {sku}: 1 image")
        else:
            print(f"  [ok] {sku}: {len(vectors)} images")
        embeddings[category][sku] = vectors
        total_imgs += len(vectors)

    print(f"\nEmbedded {total_imgs} images across {len(embeddings)} categories.\n")

    # --- 2. leave-one-out retrieval --------------------------------------
    per_category: dict[str, dict[str, float]] = {}
    all_ranks: list[int] = []
    misses: list[tuple[str, str, str, float]] = []  # (sku, img#, predicted, score)

    for category, skus in sorted(embeddings.items()):
        sku_list = list(skus)
        ranks: list[int] = []

        for true_sku, vecs in skus.items():
            if len(vecs) < 2:
                continue  # distractor-only: nothing left once held out
            for i, query in enumerate(vecs):
                # Centroid per SKU (as FaissIndex.search scores), with the
                # query itself excluded from its own product's centroid.
                scores = []
                for sku in sku_list:
                    pool = [
                        v
                        for j, v in enumerate(skus[sku])
                        if sku != true_sku or j != i
                    ]
                    if not pool:
                        continue
                    scores.append((sku, float(np.dot(query, unit(np.mean(np.stack(pool), axis=0))))))
                scores.sort(key=lambda x: -x[1])

                rank = next(r for r, (sku, _) in enumerate(scores, 1) if sku == true_sku)
                ranks.append(rank)
                all_ranks.append(rank)
                if rank != 1:
                    misses.append((true_sku, f"img{i + 1}", scores[0][0], scores[0][1]))

        n = len(ranks)
        if not n:
            print(f"  [skip] {category}: no queryable products (all single-image)")
            continue
        per_category[category] = {
            "n": n,
            "products": len(sku_list),
            "top1": sum(r == 1 for r in ranks) / n * 100,
            "top3": sum(r <= 3 for r in ranks) / n * 100,
            "mrr": sum(1 / r for r in ranks) / n,
        }

    # --- 3. report --------------------------------------------------------
    print("=" * 72)
    print("BRAIN 2 RETRIEVAL ACCURACY (leave-one-out)")
    print("=" * 72)
    print(f"{'Category':24}{'SKUs':>5}{'Queries':>9}{'Top-1':>9}{'Top-3':>9}{'MRR':>7}")
    print("-" * 72)
    for cat, m in sorted(per_category.items()):
        print(f"{cat:24}{m['products']:>5}{m['n']:>9}"
              f"{m['top1']:>8.1f}%{m['top3']:>8.1f}%{m['mrr']:>7.3f}")
    print("-" * 72)

    n = len(all_ranks)
    top1 = sum(r == 1 for r in all_ranks) / n * 100
    top3 = sum(r <= 3 for r in all_ranks) / n * 100
    mrr = sum(1 / r for r in all_ranks) / n
    print(f"{'OVERALL':24}{sum(m['products'] for m in per_category.values()):>5}{n:>9}"
          f"{top1:>8.1f}%{top3:>8.1f}%{mrr:>7.3f}")
    print("=" * 72)

    if misses:
        print(f"\nMisses ({len(misses)}) - correct SKU was not ranked first:")
        for true_sku, img, predicted, score in misses[:25]:
            print(f"   {true_sku:10} {img:6} -> predicted {predicted:10} ({score:.3f})")
        if len(misses) > 25:
            print(f"   ... and {len(misses) - 25} more")


if __name__ == "__main__":
    main()
