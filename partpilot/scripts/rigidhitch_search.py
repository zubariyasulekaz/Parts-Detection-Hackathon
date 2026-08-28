"""Search the RigidHitch index with a photograph.

The end of the pipeline: a photo goes in, ranked products come out. Runs against
the built index without the API, the database or the frontend, so a real phone
photo can be tested long before any of that is wired up - which matters, because
every accuracy figure so far comes from catalogue photos matched against
catalogue photos, and nobody yet knows what a workbench snapshot does to them.

The query is put through exactly what the catalogue vectors went through:
background removal, the same embedding model, the same TTA setting, and the same
whitening matrix. Any of those differing silently makes the comparison
meaningless rather than merely worse, which is why the build settings are read
from the index's own sidecar rather than assumed.

Run:
    python scripts/rigidhitch_search.py path/to/photo.jpg
    python scripts/rigidhitch_search.py photo.jpg --top-k 10 --no-remove-bg
"""

import argparse
import csv
import json
import sys
from pathlib import Path

import numpy as np
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from backend.pipeline.brain2_similarity.embedding_generator import (  # noqa: E402
    EmbeddingGenerator,
)
from backend.utils.image_utils import remove_background  # noqa: E402

DEFAULT_INDEX_DIR = Path(__file__).resolve().parent.parent / "backend" / "models" / "faiss_rigidhitch"
DEFAULT_CATALOG = Path(
    r"C:\Users\Vasuki.KLIZER-49\Downloads\rigidhitch_dataset\rigidhitch_dataset\catalog.clean.csv"
)
INDEX_NAME = "rigidhitch"
# Below this gap between the best and second-best product the model is not really
# choosing - it is split between near-identical parts, most often the same item in
# a different size, which a photograph cannot show.
#
# Set from the measured margin distribution rather than picked: this is the 30th
# percentile, where top-1 is right 19.2% of the time against 47.4% above it. An
# earlier 0.02 (the 20th percentile) was too tight - it let through a hub-cap query
# whose top two differed only in diameter, exactly the case worth flagging.
AMBIGUOUS_MARGIN = 0.036


def load_index(index_dir: Path) -> tuple[np.ndarray, list[str], dict]:
    """Per-SKU centroids, their SKUs, and how the index was built."""
    import faiss  # noqa: PLC0415

    build = json.loads((index_dir / f"{INDEX_NAME}.build.json").read_text())
    skus_per_row = json.loads((index_dir / f"{INDEX_NAME}.ids.json").read_text())
    index = faiss.read_index(str(index_dir / f"{INDEX_NAME}.faiss"))
    vectors = index.reconstruct_n(0, index.ntotal)

    grouped: dict[str, list[int]] = {}
    for row, sku in enumerate(skus_per_row):
        grouped.setdefault(sku, []).append(row)

    skus = sorted(grouped)
    centroids = np.stack([vectors[grouped[s]].mean(axis=0) for s in skus])
    norms = np.linalg.norm(centroids, axis=1, keepdims=True)
    norms[norms == 0] = 1.0
    return centroids / norms, skus, build


def embed_query(path: Path, build: dict, strip_background: bool) -> np.ndarray:
    """Put the query through the identical treatment the catalogue vectors had."""
    with Image.open(path) as handle:
        image = handle.convert("RGB")
    if strip_background:
        image = remove_background(image)

    generator = EmbeddingGenerator(backend_spec=build["backend"])
    return np.asarray(generator.generate(image, tta=build["tta"]), dtype=np.float32)


def whiten_query(vector: np.ndarray, index_dir: Path) -> np.ndarray:
    """Apply the stored whitening transform. Without it the query is not comparable."""
    path = index_dir / f"{INDEX_NAME}.whiten.npz"
    if not path.is_file():
        return vector
    stored = np.load(path)
    whitened = (vector - stored["mean"]) @ stored["matrix"]
    norm = np.linalg.norm(whitened)
    return (whitened / norm if norm else whitened).astype(np.float32)


def load_names(path: Path) -> dict[str, tuple[str, str]]:
    if not path.is_file():
        return {}
    names: dict[str, tuple[str, str]] = {}
    with path.open(newline="", encoding="utf-8-sig") as handle:
        for row in csv.DictReader(handle):
            names[row["sku"].strip()] = (
                (row.get("product_name") or "").strip(),
                (row.get("category") or "").strip(),
            )
    return names


def main() -> None:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("photo", type=Path)
    parser.add_argument("--index-dir", type=Path, default=DEFAULT_INDEX_DIR)
    parser.add_argument("--catalog", type=Path, default=DEFAULT_CATALOG)
    parser.add_argument("--top-k", type=int, default=5)
    parser.add_argument("--no-remove-bg", action="store_true",
                        help="Skip background removal, to measure what it is worth.")
    args = parser.parse_args()

    if not args.photo.is_file():
        raise SystemExit(f"photo not found: {args.photo}")

    centroids, skus, build = load_index(args.index_dir)
    print(f"index: {len(skus):,} products  ({build['backend']}, "
          f"tta={build['tta']}, whitening={'on' if build.get('whitening') else 'off'})")

    strip_bg = build.get("remove_bg", True) and not args.no_remove_bg
    vector = embed_query(args.photo, build, strip_bg)
    if build.get("whitening"):
        vector = whiten_query(vector, args.index_dir)

    if vector.shape[0] != centroids.shape[1]:
        raise SystemExit(
            f"query is {vector.shape[0]}-dim but the index is {centroids.shape[1]}-dim. "
            "The query was not put through the same transform as the index."
        )

    scores = centroids @ vector
    order = np.argsort(-scores)[: max(args.top_k, 2)]
    names = load_names(args.catalog)

    print(f"\n{args.photo.name}  (background removal: {'on' if strip_bg else 'off'})\n")
    for rank, position in enumerate(order[: args.top_k], start=1):
        sku = skus[position]
        name, category = names.get(sku, ("", ""))
        print(f"  {rank}. {sku:<18} {scores[position]:.3f}  {name[:52]}")
        if category:
            print(f"     {'':<18} {'':<6}  {category}")

    margin = float(scores[order[0]] - scores[order[1]])
    print(f"\ntop-2 margin: {margin:.4f}")
    if margin < AMBIGUOUS_MARGIN:
        print("AMBIGUOUS - the top two are near-indistinguishable. In production this")
        print("is where the shortlist should be shown, or the vehicle asked for,")
        print("rather than asserting the first result.")


if __name__ == "__main__":
    main()
