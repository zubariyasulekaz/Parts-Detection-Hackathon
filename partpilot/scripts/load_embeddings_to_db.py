"""Copy the vectors out of the FAISS indexes into the products table.

Reuses the vectors that are already built rather than re-embedding every
image, so this takes seconds instead of the ten minutes a rebuild costs.

Each index knows which model produced it (the .meta.json sidecar written by
build_faiss_indexes.py), and the two models disagree on vector length -
DINOv2 gives 768, OpenCLIP 512 - so a row's vector goes into whichever column
matches and `embedding_backend` records the model. A query then has to be
embedded with the same model as the row it is compared against; mixing them
does not error, it just returns confident nonsense.

Run after `alembic upgrade head`:
    python scripts/load_embeddings_to_db.py
    python scripts/load_embeddings_to_db.py --dry-run
"""

import argparse
import asyncio
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import text  # noqa: E402

from backend.config.paths import FAISS_MODEL_DIR  # noqa: E402
from backend.config.settings import get_settings  # noqa: E402
from backend.core.database import engine  # noqa: E402

#: pgvector accepts its literal form, "[0.1,0.2,...]".
DIM_COLUMN = {768: "embedding_768", 512: "embedding_512"}


def read_indexes() -> list[dict]:
    """Pull (sku, vector, backend) out of every FAISS index on disk."""
    try:
        import faiss  # noqa: PLC0415
    except ImportError as exc:  # pragma: no cover - env-dependent
        raise SystemExit("faiss-cpu is not installed; cannot read the indexes.") from exc

    rows: list[dict] = []
    for index_path in sorted(FAISS_MODEL_DIR.glob("*.faiss")):
        stem = index_path.stem
        ids_path = index_path.with_name(f"{stem}.ids.json")
        meta_path = index_path.with_name(f"{stem}.meta.json")
        if not ids_path.exists():
            print(f"  [skip] {stem}: no .ids.json sidecar")
            continue

        skus = json.loads(ids_path.read_text(encoding="utf-8"))
        backend = (
            json.loads(meta_path.read_text(encoding="utf-8")).get("backend")
            if meta_path.exists() else None
        )
        if not backend:
            print(f"  [skip] {stem}: no .meta.json, so the model is unknown")
            continue

        index = faiss.read_index(str(index_path))
        if index.d not in DIM_COLUMN:
            print(f"  [skip] {stem}: {index.d}-dim vectors have no column")
            continue

        vectors = index.reconstruct_n(0, index.ntotal)
        for sku, vector in zip(skus, vectors):
            rows.append({
                "sku": sku,
                "dim": index.d,
                "backend": backend,
                # pgvector's text input format
                "vector": "[" + ",".join(f"{v:.8f}" for v in vector) + "]",
            })
        print(f"  {stem:22} {index.ntotal:2} vectors, {index.d}-dim, {backend}")

    return rows


async def write(rows: list[dict]) -> int:
    """Write each vector into the column matching its length."""
    updated = 0
    async with engine.begin() as connection:
        for row in rows:
            column = DIM_COLUMN[row["dim"]]
            result = await connection.execute(
                text(
                    f"UPDATE products SET {column} = :vector, embedding_backend = :backend "
                    "WHERE sku = :sku"
                ),
                {"vector": row["vector"], "backend": row["backend"], "sku": row["sku"]},
            )
            updated += result.rowcount
    return updated


async def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true",
                        help="Read the indexes and report, without writing.")
    args = parser.parse_args()

    print("Reading FAISS indexes...")
    rows = read_indexes()
    if not rows:
        raise SystemExit("No vectors found. Build the indexes first.")

    by_dim: dict[int, int] = {}
    for row in rows:
        by_dim[row["dim"]] = by_dim.get(row["dim"], 0) + 1
    print(f"\n{len(rows)} vectors total: " +
          ", ".join(f"{n} x {d}-dim" for d, n in sorted(by_dim.items())))

    if args.dry_run:
        print("\nDry run - nothing written.")
        example = rows[0]
        print(f"Example: {example['sku']} ({example['backend']}, {example['dim']}-dim)")
        print(f"  {example['vector'][:70]}...")
        return

    url = get_settings().DATABASE_URL
    print(f"\nWriting to {re.sub(r'://[^@]+@', '://***@', url)}")
    try:
        updated = await write(rows)
    except Exception as exc:  # noqa: BLE001
        raise SystemExit(
            f"\nFailed: {type(exc).__name__}: {exc}\n\n"
            "If the embedding columns are missing, run: alembic upgrade head"
        ) from exc
    finally:
        await engine.dispose()

    print(f"Updated {updated} product rows.")
    if updated != len(rows):
        missing = len(rows) - updated
        print(f"  [warn] {missing} vectors matched no product row - the indexes "
              "and the catalog may have drifted apart.")


if __name__ == "__main__":
    asyncio.run(main())
