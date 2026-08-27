"""Embed RigidHitch's de-duplicated images, checkpointing as it goes.

Reads the row manifest written by ``rigidhitch_dedup_images.py`` and produces
one vector per row, in the same order, so row N of the array is line N of the
manifest. That ordering is the entire contract between the two halves of the
pipeline; ``embeddings.meta.json`` records a hash of the manifest so a
mismatched pair fails loudly instead of building a silently misaligned index.

Vectors go through the real ``EmbeddingGenerator``, not a reimplementation.
Preprocessing and TTA must match what the runtime does to a query image or the
two are not comparable, and the cheapest way to guarantee that is to call the
same code.

Designed for Colab: results are flushed to disk every ``--shard-size`` rows and
completed shards are recorded, so a disconnected session resumes from the last
shard rather than starting over. Point ``--out-dir`` at Drive and the images at
local SSD - per-file Drive I/O across 17k small files costs more than the
embedding.

Run:
    python scripts/rigidhitch_embed_images.py --limit 200      # smoke test first
    python scripts/rigidhitch_embed_images.py
"""

import argparse
import hashlib
import json
import sys
import time
from pathlib import Path

import numpy as np
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from backend.config.settings import get_settings  # noqa: E402
from backend.pipeline.brain2_similarity.embedding_generator import (  # noqa: E402
    EmbeddingGenerator,
)

DEFAULT_IMAGES_DIR = Path(
    r"C:\Users\Vasuki.KLIZER-49\Downloads\images_clean\images_clean"
)
DEFAULT_BUILD_DIR = Path(
    r"C:\Users\Vasuki.KLIZER-49\Downloads\rigidhitch_dataset\rigidhitch_dataset\index_build"
)
SHARD_SIZE = 2048


def manifest_digest(path: Path) -> str:
    """SHA-256 of the manifest file, binding an embedding array to its rows."""
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_rows(path: Path) -> list[dict]:
    if not path.is_file():
        raise SystemExit(
            f"row manifest not found: {path}\nRun scripts/rigidhitch_dedup_images.py first."
        )
    with path.open(encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]


def shard_path(shard_dir: Path, index: int) -> Path:
    return shard_dir / f"shard_{index:05d}.npy"


def completed_shards(shard_dir: Path) -> set[int]:
    """Shards already written, read from the sidecar rather than by globbing.

    A ``.npy`` can exist but be truncated if the session died mid-write; only
    shards recorded here were written whole and renamed into place.
    """
    done_file = shard_dir / "shards.done.json"
    if not done_file.is_file():
        return set()
    return set(json.loads(done_file.read_text()))


def record_shard(shard_dir: Path, index: int) -> None:
    done_file = shard_dir / "shards.done.json"
    done = sorted(completed_shards(shard_dir) | {index})
    done_file.write_text(json.dumps(done))


def embed_shard(
    rows: list[dict],
    images_dir: Path,
    generator: EmbeddingGenerator,
    dim: int | None,
) -> tuple[np.ndarray, int]:
    """Embed one shard's rows in manifest order.

    An unreadable image yields a zero vector rather than shifting every later
    row up by one - the array must stay aligned with the manifest whatever
    happens. Zero rows are reported and skipped at build time.
    """
    vectors: list[np.ndarray] = []
    failures = 0

    for row in rows:
        path = images_dir / row["rel"]
        try:
            with Image.open(path) as handle:
                vector = generator.generate(handle.convert("RGB"))
            vectors.append(np.asarray(vector, dtype=np.float32))
            if dim is None:
                dim = vectors[-1].shape[0]
        except Exception as exc:  # noqa: BLE001
            print(f"    [skip] {row['rel']}: {type(exc).__name__}: {exc}", flush=True)
            failures += 1
            vectors.append(np.zeros(dim or 0, dtype=np.float32))

    return np.stack(vectors), failures


def main() -> None:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--images-dir", type=Path, default=DEFAULT_IMAGES_DIR)
    parser.add_argument("--build-dir", type=Path, default=DEFAULT_BUILD_DIR,
                        help="Holds embed_rows.jsonl; embeddings are written here too.")
    parser.add_argument("--backend", default=None,
                        help="Embedding backend spec, e.g. dinov2. Default: EMBEDDING_BACKEND.")
    parser.add_argument("--shard-size", type=int, default=SHARD_SIZE)
    parser.add_argument("--limit", type=int, default=None,
                        help="Embed only the first N rows - for the smoke test.")
    args = parser.parse_args()

    rows_path = args.build_dir / "embed_rows.jsonl"
    rows = load_rows(rows_path)
    if args.limit:
        rows = rows[: args.limit]

    generator = EmbeddingGenerator(backend_spec=args.backend)
    backend_name = generator.backend_name
    tta = get_settings().EMBEDDING_TTA

    suffix = "_smoke" if args.limit else ""
    shard_dir = args.build_dir / "embeddings" / f"{backend_name}{suffix}"
    shard_dir.mkdir(parents=True, exist_ok=True)

    total_shards = (len(rows) + args.shard_size - 1) // args.shard_size
    done = completed_shards(shard_dir)
    print(f"{len(rows):,} rows -> {total_shards} shards of {args.shard_size:,}")
    print(f"backend={backend_name}  tta={tta}  images={args.images_dir}")
    if done:
        print(f"resuming: {len(done)} shard(s) already complete")

    dim: int | None = None
    failures = 0
    embedded_now = 0
    started = time.time()

    for shard_index in range(total_shards):
        if shard_index in done:
            continue
        chunk = rows[shard_index * args.shard_size : (shard_index + 1) * args.shard_size]
        array, shard_failures = embed_shard(chunk, args.images_dir, generator, dim)
        dim = dim or array.shape[1]
        failures += shard_failures

        # Write to a temp name and rename, so a kill mid-write can never leave a
        # half-written shard that later looks complete.
        temp = shard_path(shard_dir, shard_index).with_suffix(".tmp.npy")
        np.save(temp, array)
        temp.replace(shard_path(shard_dir, shard_index))
        record_shard(shard_dir, shard_index)

        # Count images actually embedded this session, not shards * shard_size:
        # a resumed run or a short final shard would otherwise report a rate
        # several times higher than reality and hide how long the run will take.
        embedded_now += len(chunk)
        elapsed = time.time() - started
        rate = embedded_now / elapsed if elapsed else 0
        remaining = len(rows) - (shard_index + 1) * args.shard_size
        eta = f", ~{remaining / rate / 60:.0f} min left" if rate and remaining > 0 else ""
        print(f"  shard {shard_index + 1}/{total_shards} written"
              f"  ({rate:.1f} img/s, {elapsed / 60:.1f} min elapsed{eta})", flush=True)

    arrays = [np.load(shard_path(shard_dir, i)) for i in range(total_shards)]
    embeddings = np.concatenate(arrays) if arrays else np.empty((0, 0), dtype=np.float32)

    out_path = args.build_dir / f"embeddings{suffix}.npy"
    np.save(out_path, embeddings)
    (args.build_dir / f"embeddings{suffix}.meta.json").write_text(json.dumps({
        "schema": 1,
        "backend": backend_name,
        "tta": tta,
        "dim": int(embeddings.shape[1]) if embeddings.size else 0,
        "rows": int(embeddings.shape[0]),
        "rows_file": rows_path.name,
        "rows_file_sha256": manifest_digest(rows_path),
        "limit": args.limit,
        "failed_images": failures,
    }, indent=2))

    zero_rows = int((np.abs(embeddings).sum(axis=1) == 0).sum()) if embeddings.size else 0
    print()
    print(f"Embedded {embeddings.shape[0]:,} rows, dim {embeddings.shape[1] if embeddings.size else 0}")
    if failures:
        print(f"  [warn] {failures} image(s) failed and are zero vectors ({zero_rows} zero rows)")
    print(f"Took {(time.time() - started) / 60:.1f} min")
    print(f"Wrote {out_path.name} + meta -> {args.build_dir}")


if __name__ == "__main__":
    main()
