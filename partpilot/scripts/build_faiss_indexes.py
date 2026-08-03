"""Build one FAISS index per product category from the image dataset.

For each SKU it averages the OpenCLIP embeddings of that product's images
into a single L2-normalized product vector (the `get_product_embedding`
approach from vector_1.py), then writes one ``<category_slug>.faiss`` index
(plus a ``.ids.json`` SKU sidecar) per category into ``backend/models/faiss/``.

Requires: ``faiss-cpu``, ``open_clip_torch``, ``torch`` (run in Colab or an
env where these are installed), and images already converted to a loadable
format (JPG/PNG) via ``scripts/convert_images_to_jpg.py``. With ``--remove-bg``
each catalog image is background-removed (rembg) so the stored vectors match
how the runtime cleans an uploaded query image.

Run:
    python scripts/build_faiss_indexes.py                # embed images as-is
    python scripts/build_faiss_indexes.py --remove-bg    # rembg first (recommended)
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


def product_embedding(
    sku_folder: Path,
    generator: EmbeddingGenerator,
    remove_bg: bool = False,
) -> np.ndarray | None:
    """Mean of per-image embeddings for one product, L2-normalized.

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

    if not vectors:
        return None
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
    cli_args = parser.parse_args()

    # Group SKU records by category.
    by_category: dict[str, list[dict]] = defaultdict(list)
    for record in load_catalog_records(CATALOG_CSV_PATH):
        category = (record.get("category") or "").strip()
        if category:
            by_category[category].append(record)

    generator = EmbeddingGenerator(backend_spec=cli_args.backend)
    print(f"Embedding backend: {generator.backend_name}")
    FAISS_MODEL_DIR.mkdir(parents=True, exist_ok=True)

    for category, records in by_category.items():
        slug = category_slug(category)
        index = FaissIndex(FAISS_MODEL_DIR / f"{slug}.faiss")
        print(f"\n[{category}] -> {slug}.faiss")

        added = 0
        for record in records:
            sku = record["sku"]
            image_folder = record.get("image_folder") or f"images/{sku}"
            sku_folder = DATASETS_DIR / image_folder
            if not sku_folder.is_dir():
                print(f"    [skip] {sku}: folder not found ({sku_folder})")
                continue

            vector = product_embedding(sku_folder, generator, remove_bg=cli_args.remove_bg)
            if vector is None:
                print(f"    [skip] {sku}: no loadable images")
                continue
            index.add(sku, vector)
            added += 1
            print(f"    [ok] {sku}")

        if added:
            index.save()
            print(f"  Saved {added} product vectors -> {index._index_path}")
        else:
            print(f"  [warn] no vectors added for '{category}', index not written")


if __name__ == "__main__":
    main()
