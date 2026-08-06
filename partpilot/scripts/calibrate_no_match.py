"""Calibrate the per-backend no-match thresholds (Settings.NO_MATCH_THRESHOLDS).

Brain 2 always returns the nearest neighbours inside a category — it cannot
say "nothing in here looks like this". The orchestrator therefore rejects a
top match whose similarity falls below a threshold. This script measures
where that threshold should sit, per embedding backend, for the current
max-over-images scoring.

Two score distributions are measured over the catalog images:

  correct   For each image, its top-1 score when queried against its OWN
            category, leave-one-out (the image is removed from its own
            product's pool). This is what an in-catalog upload scores.

  impostor  For each image, its top-1 score when queried against every
            OTHER category that uses the same embedding backend. This is
            what an out-of-catalog upload (or a Brain 1 misroute) scores:
            the part genuinely is not in the index being searched.

A good threshold rejects ~none of the correct distribution while catching as
much of the impostor distribution as possible. The sweep prints both rates
for a range of thresholds, per backend, and recommends the highest threshold
that keeps correct-match rejection at zero.

Run (must match how the indexes were built):
    python scripts/calibrate_no_match.py --remove-bg
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
    path = DATASETS_DIR / "catalog.csv"
    if not path.is_file():
        raise SystemExit(f"catalog.csv not found: {path}")
    with path.open(newline="", encoding="utf-8-sig") as f:
        return [row for row in csv.DictReader(f) if (row.get("sku") or "").strip()]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--remove-bg",
        action="store_true",
        help="Background-remove each image first (use this if the indexes were built with --remove-bg).",
    )
    args = parser.parse_args()

    records = load_catalog()
    backends = BackendCache()
    generators: dict[str, EmbeddingGenerator] = {}

    def generator_for(spec: str) -> EmbeddingGenerator:
        if spec not in generators:
            generators[spec] = EmbeddingGenerator(backend=backends.get(spec))
        return generators[spec]

    # Which backend each category's index uses.
    category_spec: dict[str, str] = {}
    for record in records:
        category = (record.get("category") or "").strip()
        if category and category not in category_spec:
            category_spec[category] = backend_for_category(category)
    specs = sorted(set(category_spec.values()))
    print(f"Backends in play: {specs}")

    # Load every image once; embed it with every backend that any category
    # uses, because an impostor query against a category is embedded with
    # THAT category's backend.
    # spec -> category -> sku -> [vector per image]
    vectors: dict[str, dict[str, dict[str, list[np.ndarray]]]] = {
        spec: defaultdict(lambda: defaultdict(list)) for spec in specs
    }

    print("Embedding catalog images with every backend...")
    for record in records:
        category = (record.get("category") or "").strip()
        sku = record["sku"]
        if not category:
            continue
        folder = DATASETS_DIR / (record.get("image_folder") or f"images/{sku}")
        if not folder.is_dir():
            print(f"  [skip] {sku}: folder not found")
            continue
        for img_path in sorted(folder.iterdir()):
            if img_path.suffix.lower() not in IMAGE_EXTS:
                continue
            try:
                with Image.open(img_path) as im:
                    im = im.convert("RGB")
                    if args.remove_bg:
                        im = remove_background(im)
                    for spec in specs:
                        vec = np.asarray(generator_for(spec).generate(im), dtype=np.float32)
                        vectors[spec][category][sku].append(vec)
            except Exception as exc:  # noqa: BLE001
                print(f"  [skip] {img_path.name}: {type(exc).__name__}: {exc}")
        print(f"  [ok] {sku}")

    # --- correct distribution: own category, leave-one-out ---------------
    correct: dict[str, list[float]] = defaultdict(list)
    for category, spec in category_spec.items():
        skus = vectors[spec][category]
        for true_sku, vecs in skus.items():
            if len(vecs) < 2:
                continue
            for i, query in enumerate(vecs):
                best = float("-inf")
                for sku, pool in skus.items():
                    for j, v in enumerate(pool):
                        if sku == true_sku and j == i:
                            continue
                        best = max(best, float(np.dot(query, v)))
                correct[spec].append(best)

    # --- impostor distribution: every other same-backend category --------
    impostor: dict[str, list[float]] = defaultdict(list)
    for target_category, spec in category_spec.items():
        target = vectors[spec][target_category]
        target_vectors = [v for pool in target.values() for v in pool]
        if not target_vectors:
            continue
        stacked = np.stack(target_vectors)
        for source_category in category_spec:
            if source_category == target_category:
                continue
            for pool in vectors[spec][source_category].values():
                for query in pool:
                    impostor[spec].append(float(np.max(stacked @ query)))

    # --- sweep ------------------------------------------------------------
    for spec in specs:
        c = np.array(correct[spec])
        i = np.array(impostor[spec])
        print()
        print("=" * 64)
        print(f"BACKEND: {spec}   (correct n={len(c)}, impostor n={len(i)})")
        print("=" * 64)
        print(
            f"correct:  min {c.min():.3f}  p5 {np.percentile(c, 5):.3f}  "
            f"median {np.median(c):.3f}  max {c.max():.3f}"
        )
        print(
            f"impostor: min {i.min():.3f}  median {np.median(i):.3f}  "
            f"p95 {np.percentile(i, 95):.3f}  max {i.max():.3f}"
        )
        print(f"\n{'threshold':>10}{'correct rejected':>18}{'impostors caught':>18}")
        best_threshold = None
        for t in np.arange(0.30, 0.96, 0.01):
            rejected = float((c < t).mean() * 100)
            caught = float((i < t).mean() * 100)
            if rejected == 0.0:
                best_threshold = t
            if abs(round(t * 100) % 5) < 1e-6 or rejected > 0:
                print(f"{t:>10.2f}{rejected:>17.1f}%{caught:>17.1f}%")
            if rejected > 5:
                break
        if best_threshold is not None:
            caught_at_best = float((i < best_threshold).mean() * 100)
            print(
                f"\nRecommended: {best_threshold:.2f} "
                f"(highest threshold rejecting 0% of correct matches; "
                f"catches {caught_at_best:.1f}% of impostors)"
            )


if __name__ == "__main__":
    main()
