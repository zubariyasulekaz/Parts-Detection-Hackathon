"""Build one FAISS index per product category from the image dataset.

By default every catalog image gets its own vector in the index (the SKU
sidecar simply repeats the SKU once per image), and a search scores each SKU
by its best-matching image. This replaced the earlier one-centroid-per-SKU
scheme (`--centroid`), where even an exact catalog photo scored only ~0.70
because it was compared against the average of its product's other photos.

Requires: ``faiss-cpu``, ``torch``, ``transformers``/``open_clip_torch``, and
images already converted to a loadable format (JPG/PNG) via
``scripts/convert_images_to_jpg.py``. With ``--remove-bg`` each catalog image
is background-removed (rembg) so the stored vectors match how the runtime
cleans an uploaded query image; the choice is recorded in the index metadata
so the query side follows it.

Run:
    python scripts/build_faiss_indexes.py --remove-bg    # recommended
    python scripts/build_faiss_indexes.py --centroid     # legacy per-SKU mean
"""

import argparse
import csv
import sys
from collections import defaultdict
from pathlib import Path

import numpy as np
from PIL import Image

# Make ``backend`` importable when run as a plain script from the repo root.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from backend.config.paths import CATALOG_CSV_PATH, DATASETS_DIR, FAISS_MODEL_DIR  # noqa: E402
from backend.pipeline.brain2_similarity.embedding_backends import (  # noqa: E402
    BackendCache,
    backend_for_category,
)
from backend.pipeline.brain2_similarity.embedding_generator import EmbeddingGenerator  # noqa: E402
from backend.pipeline.brain2_similarity.faiss_index import FaissIndex  # noqa: E402
from backend.pipeline.brain2_similarity.index_manager import category_slug  # noqa: E402
from backend.utils.image_utils import remove_background  # noqa: E402

IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".webp"}


def load_catalog_records(csv_path: Path) -> list[dict]:
    """Read every row of the catalog CSV into a plain dict.

    A standalone reader (rather than the app's DB-backed catalog service)
    since this is an offline batch job that only needs `sku`/`category`/
    `image_folder` columns straight from the CSV.
    """
    with csv_path.open("r", newline="", encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))


def image_embeddings(
    sku_folder: Path,
    generator: EmbeddingGenerator,
    remove_bg: bool = False,
) -> list[np.ndarray]:
    """One embedding per loadable image in a SKU's folder.

    If ``remove_bg`` is set, each image is background-removed before
    embedding, matching the runtime query preprocessing.
    """
    vectors: list[np.ndarray] = []
    for img_path in sorted(sku_folder.iterdir()):
        if img_path.suffix.lower() not in IMAGE_EXTS:
            continue
        try:
            with Image.open(img_path) as im:
                im = im.convert("RGB")
                if remove_bg:
                    im = remove_background(im)
                vectors.append(generator.generate(im))
        except Exception as exc:  # noqa: BLE001
            print(f"    [skip] {img_path.name}: {type(exc).__name__}: {exc}")
    return vectors


def centroid(vectors: list[np.ndarray]) -> np.ndarray:
    """Mean of per-image embeddings, L2-normalized (legacy per-SKU vector)."""
    mean = np.mean(np.stack(vectors), axis=0)
    norm = np.linalg.norm(mean)
    return mean / norm if norm else mean


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--remove-bg",
        action="store_true",
        help="Background-remove each catalog image (rembg) before embedding.",
    )
    parser.add_argument(
        "--backend",
        default=None,
        help="Embedding model to build with, e.g. dinov2, siglip, 'dinov2+siglip'. "
             "Default: whatever EMBEDDING_BACKEND is set to. Indexes built with "
             "one backend cannot be queried with another.",
    )
    parser.add_argument(
        "--centroid",
        action="store_true",
        help="Legacy mode: one mean-of-images vector per SKU instead of one "
             "vector per image.",
    )
    cli_args = parser.parse_args()

    # Group SKU records by category.
    by_category: dict[str, list[dict]] = defaultdict(list)
    for record in load_catalog_records(CATALOG_CSV_PATH):
        category = (record.get("category") or "").strip()
        if category:
            by_category[category].append(record)

    # Each category may use a different model (see CATEGORY_BACKENDS), so build
    # generators lazily and reuse them - loading a vision transformer is slow.
    backends = BackendCache()
    generators: dict[str, EmbeddingGenerator] = {}

    def generator_for(spec: str) -> EmbeddingGenerator:
        if spec not in generators:
            generators[spec] = EmbeddingGenerator(backend=backends.get(spec))
        return generators[spec]

    FAISS_MODEL_DIR.mkdir(parents=True, exist_ok=True)

    for category, records in by_category.items():
        slug = category_slug(category)
        # --backend forces one model for everything; otherwise per-category.
        spec = cli_args.backend or backend_for_category(category)
        generator = generator_for(spec)
        index = FaissIndex(FAISS_MODEL_DIR / f"{slug}.faiss")
        print(f"\n[{category}] -> {slug}.faiss  (backend: {generator.backend_name})")

        added_skus = 0
        added_vectors = 0
        for record in records:
            sku = record["sku"]
            image_folder = record.get("image_folder") or f"images/{sku}"
            sku_folder = DATASETS_DIR / image_folder
            if not sku_folder.is_dir():
                print(f"    [skip] {sku}: folder not found ({sku_folder})")
                continue

            vectors = image_embeddings(sku_folder, generator, remove_bg=cli_args.remove_bg)
            if not vectors:
                print(f"    [skip] {sku}: no loadable images")
                continue
            if cli_args.centroid:
                vectors = [centroid(vectors)]
            for vector in vectors:
                index.add(sku, vector)
            added_skus += 1
            added_vectors += len(vectors)
            print(f"    [ok] {sku} ({len(vectors)} vectors)")

        if added_skus:
            # Record how the index was built so the query side matches it.
            index.save(backend=generator.backend_name, remove_bg=cli_args.remove_bg)
            print(
                f"  Saved {added_vectors} vectors across {added_skus} SKUs -> {index._index_path}"
            )
        else:
            print(f"  [warn] no vectors added for '{category}', index not written")


if __name__ == "__main__":
    main()
