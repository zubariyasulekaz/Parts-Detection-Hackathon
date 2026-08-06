"""Upload catalog photos to Supabase Storage and point the catalog at them.

Brain 3 stores `image_paths` as paths relative to datasets/ ("images/AFR-001/
AFR-001-1.jpg"), which only resolve on a machine that has the images zip. The
frontend renders nothing for them: `utils/format.ts` only accepts absolute
http/https URLs, so a relative path is filtered out and the product shows a
placeholder.

Uploading to a public Storage bucket fixes both problems at once - the images
live somewhere every teammate can reach, and the stored URL is absolute, so the
frontend renders it with no code change.

Safe to re-run. Uploads use upsert, so re-running overwrites rather than
failing, and rows whose `image_paths` are already public URLs are left alone
unless --force is passed.

Needs SUPABASE_URL and SUPABASE_SERVICE_KEY in partpilot/.env. The service key
bypasses row-level security - keep it out of git and out of the frontend.

Run:
    python scripts/upload_images_to_supabase.py --dry-run   # report only
    python scripts/upload_images_to_supabase.py
"""

import argparse
import asyncio
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import httpx  # noqa: E402
from dotenv import load_dotenv  # noqa: E402
from sqlalchemy import text  # noqa: E402

from backend.config.paths import DATASETS_DIR  # noqa: E402
from backend.core.database import engine  # noqa: E402

IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".webp"}
CONTENT_TYPES = {
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".png": "image/png",
    ".webp": "image/webp",
}
DEFAULT_BUCKET = "product-images"


def load_credentials() -> tuple[str, str]:
    """Read the Storage credentials from the environment/.env."""
    load_dotenv(Path(__file__).resolve().parent.parent / ".env")
    url = (os.getenv("SUPABASE_URL") or "").strip().rstrip("/")
    key = (os.getenv("SUPABASE_SERVICE_KEY") or "").strip()
    if not url or not key:
        raise SystemExit(
            "SUPABASE_URL and SUPABASE_SERVICE_KEY must be set in partpilot/.env.\n"
            "Find them in the Supabase dashboard under Project Settings -> API."
        )
    return url, key


def local_images() -> dict[str, list[Path]]:
    """Every catalog image on disk, grouped by SKU folder name."""
    root = DATASETS_DIR / "images"
    if not root.is_dir():
        raise SystemExit(
            f"No images found at {root}. Extract partpilot_images_v3.zip into "
            f"{DATASETS_DIR} first."
        )
    return {
        folder.name: sorted(f for f in folder.iterdir() if f.suffix.lower() in IMAGE_EXTS)
        for folder in sorted(root.iterdir())
        if folder.is_dir()
    }


def ensure_bucket(client: httpx.Client, bucket: str) -> None:
    """Create the bucket public if it does not already exist."""
    existing = client.get("/storage/v1/bucket")
    existing.raise_for_status()
    if any(b.get("name") == bucket for b in existing.json()):
        print(f"bucket '{bucket}' already exists")
        return

    created = client.post(
        "/storage/v1/bucket",
        json={"id": bucket, "name": bucket, "public": True},
    )
    created.raise_for_status()
    print(f"created public bucket '{bucket}'")


def upload(client: httpx.Client, bucket: str, key: str, path: Path) -> None:
    """Upload one file, overwriting whatever is already at that key."""
    response = client.post(
        f"/storage/v1/object/{bucket}/{key}",
        content=path.read_bytes(),
        headers={
            "Content-Type": CONTENT_TYPES.get(path.suffix.lower(), "application/octet-stream"),
            # Without this a re-run fails with "The resource already exists".
            "x-upsert": "true",
        },
    )
    response.raise_for_status()


async def update_catalog(public_urls: dict[str, list[str]], force: bool) -> tuple[int, int]:
    """Repoint each product's image_paths at its uploaded URLs."""
    updated = skipped = 0
    async with engine.begin() as conn:
        rows = (await conn.execute(text("select sku, image_paths from products"))).all()
        for sku, current in rows:
            urls = public_urls.get(sku)
            if not urls:
                continue
            already_hosted = bool(current) and all(str(p).startswith("http") for p in current)
            if already_hosted and not force:
                skipped += 1
                continue
            await conn.execute(
                text("update products set image_paths = :paths where sku = :sku"),
                {"paths": urls, "sku": sku},
            )
            updated += 1
    return updated, skipped


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bucket", default=DEFAULT_BUCKET, help="Storage bucket name.")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Report what would be uploaded without uploading or touching the database.",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Rewrite image_paths even for products that already point at hosted URLs.",
    )
    args = parser.parse_args()

    by_sku = local_images()
    total = sum(len(v) for v in by_sku.values())
    print(f"found {total} images across {len(by_sku)} SKU folders in {DATASETS_DIR / 'images'}")

    if args.dry_run:
        for sku, files in list(by_sku.items())[:3]:
            print(f"  {sku}: {[f.name for f in files]}")
        print(f"  ... would upload {total} files to bucket '{args.bucket}' and update image_paths")
        return

    base_url, service_key = load_credentials()
    public_urls: dict[str, list[str]] = {}

    with httpx.Client(
        base_url=base_url,
        headers={"Authorization": f"Bearer {service_key}", "apikey": service_key},
        timeout=60.0,
    ) as client:
        ensure_bucket(client, args.bucket)

        done = 0
        for sku, files in by_sku.items():
            urls = []
            for path in files:
                key = f"{sku}/{path.name}"
                upload(client, args.bucket, key, path)
                urls.append(f"{base_url}/storage/v1/object/public/{args.bucket}/{key}")
                done += 1
            public_urls[sku] = urls
            print(f"  uploaded {sku} ({len(files)} files)  [{done}/{total}]")

        # Prove the bucket really is publicly readable before rewriting the
        # catalog - a private bucket would leave every product with a dead URL.
        sample = next(iter(public_urls.values()))[0]
        check = httpx.get(sample, timeout=30.0)
        if check.status_code != 200:
            raise SystemExit(
                f"Uploaded, but {sample} returned {check.status_code}. The bucket is not public; "
                "catalog left unchanged."
            )
        print(f"public read verified: {sample}")

    updated, skipped = asyncio.run(update_catalog(public_urls, args.force))
    print(f"catalog updated: {updated} products repointed, {skipped} already hosted (use --force)")


if __name__ == "__main__":
    main()
