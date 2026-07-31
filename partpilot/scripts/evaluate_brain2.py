"""Measure Brain 2 (similarity search) retrieval accuracy, leave-one-out.

For every catalog image we ask: "if a customer uploaded THIS photo, would the
system return the right SKU?" To make that honest, the held-out photo is
excluded from its own product's fingerprint — otherwise we would be matching
a photo against a vector that literally contains it, and accuracy would be a
meaningless ~100%.

Method (mirrors ``build_faiss_indexes.py`` exactly):
  1. Embed every catalog image once (rembg -> OpenCLIP), cached in memory.
  2. For each image i of product P, in P's category:
       - P's vector      = L2-normalized mean of P's OTHER images
       - every other SKU = L2-normalized mean of ALL its images
       - score           = cosine(query_i, each product vector)
     Cosine on L2-normalized vectors is exactly what ``IndexFlatIP`` computes,
     so these numbers match what FAISS would return.
  3. Record the rank of the correct SKU.

Reported metrics:
  Top-1  - correct SKU ranked first        (the headline number)
  Top-3  - correct SKU in the top 3
  MRR    - mean reciprocal rank (1.0 = always first, 0.5 = usually second)

Run:
    python scripts/evaluate_brain2.py               # embed images as-is
    python scripts/evaluate_brain2.py --remove-bg   # match how the index was built
"""

import argparse
import sys
from collections import defaultdict
from pathlib import Path

import numpy as np
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from backend.config.paths import DATASETS_DIR  # noqa: E402
from backend.pipeline.brain2_similarity.embedding_generator import EmbeddingGenerator  # noqa: E402
from backend.pipeline.brain3_catalog.metadata_loader import MetadataLoader  # noqa: E402
from backend.utils.image_utils import remove_background  # noqa: E402

IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".webp"}


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
    args = parser.parse_args()

    loader = MetadataLoader()
    generator = EmbeddingGenerator()

    # --- 1. embed every catalog image once -------------------------------
    # category -> sku -> [embedding per image]
    embeddings: dict[str, dict[str, list[np.ndarray]]] = defaultdict(dict)
    total_imgs = 0

    print("Embedding catalog images...")
    for record in loader.all_records():
        category = (record.get("category") or "").strip()
        sku = record["sku"]
        if not category:
            continue
        folder = DATASETS_DIR / (record.get("image_folder") or f"images/{sku}")
        if not folder.is_dir():
            print(f"  [skip] {sku}: folder not found")
            continue

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

        if len(vectors) < 2:
            # Leave-one-out needs at least 2 images: one to query, one to build with.
            print(f"  [skip] {sku}: needs >=2 images (has {len(vectors)})")
            continue
        embeddings[category][sku] = vectors
        total_imgs += len(vectors)
        print(f"  [ok] {sku}: {len(vectors)} images")

    print(f"\nEmbedded {total_imgs} images across {len(embeddings)} categories.\n")

    # --- 2. leave-one-out retrieval --------------------------------------
    per_category: dict[str, dict[str, float]] = {}
    all_ranks: list[int] = []
    misses: list[tuple[str, str, str, float]] = []  # (sku, img#, predicted, score)

    for category, skus in sorted(embeddings.items()):
        # Full-mean vector for every product (used for all the "other" SKUs).
        full = {sku: unit(np.mean(np.stack(vs), axis=0)) for sku, vs in skus.items()}
        sku_list = list(skus)
        ranks: list[int] = []

        for true_sku, vecs in skus.items():
            for i, query in enumerate(vecs):
                # Rebuild the true product's vector WITHOUT the query image.
                held_out = [v for j, v in enumerate(vecs) if j != i]
                loo = unit(np.mean(np.stack(held_out), axis=0))

                scores = []
                for sku in sku_list:
                    vec = loo if sku == true_sku else full[sku]
                    scores.append((sku, float(np.dot(query, vec))))
                scores.sort(key=lambda x: -x[1])

                rank = next(r for r, (sku, _) in enumerate(scores, 1) if sku == true_sku)
                ranks.append(rank)
                all_ranks.append(rank)
                if rank != 1:
                    misses.append((true_sku, f"img{i + 1}", scores[0][0], scores[0][1]))

        n = len(ranks)
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
