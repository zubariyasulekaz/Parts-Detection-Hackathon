"""Scrape additional training images for under-represented Brain 1 categories.

Downloads candidate images via DuckDuckGo image search (same approach as
`download_images.py`) into a staging folder per category, to be cleaned
by `filter_dataset_clip.py`-style CLIP filtering before merging into the
main `dataset/` split.
"""

import os
import time
from io import BytesIO

import requests
from ddgs import DDGS
from PIL import Image

STAGING_DIR = "staging_scrape"
IMAGES_PER_CLASS = 200

QUERIES = {
    "fuel_injector": [
        "fuel injector product photo",
        "car fuel injector isolated white background",
        "OEM fuel injector",
        "diesel fuel injector",
        "gasoline direct injection injector",
        "fuel injector nozzle",
        "Bosch fuel injector",
        "Denso fuel injector",
        "fuel injector replacement part",
        "fuel injector rail assembly",
        "used fuel injector auto part",
        "new fuel injector auto part",
        "fuel injector isolated on white",
        "multi port fuel injector",
        "fuel injector connector part",
        "throttle body fuel injector",
        "common rail fuel injector",
        "fuel injector unit automotive",
        "port fuel injector",
        "fuel injector spare part",
    ],
    "suspension_bushing": [
        "suspension bushing product photo",
        "car suspension bushing isolated white background",
        "OEM suspension bushing",
        "rubber suspension bushing part",
        "polyurethane suspension bushing",
        "control arm bushing part",
        "front suspension bushing",
        "rear suspension bushing",
        "suspension arm bushing replacement",
        "vehicle suspension bushing auto part",
        "new suspension bushing",
        "used suspension bushing",
        "suspension bushing kit",
        "MOOG suspension bushing",
        "Febi suspension bushing",
        "Lemforder suspension bushing",
        "TRW suspension bushing",
        "suspension bushing spare part",
        "suspension bushing white background",
        "car suspension bushing product",
    ],
}


def download_images() -> None:
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}

    for category, search_queries in QUERIES.items():
        print(f"\n--- Fetching images for: {category} ---")
        save_dir = os.path.join(STAGING_DIR, category)
        os.makedirs(save_dir, exist_ok=True)

        count = len(os.listdir(save_dir))
        downloaded_urls = set()
        ddgs = DDGS()

        for search_query in search_queries:
            if count >= IMAGES_PER_CLASS:
                break

            print(f"\nSearching: {search_query}")
            retries = 0
            max_retries = 3

            while retries < max_retries:
                try:
                    results = list(ddgs.images(search_query, max_results=60))
                    print(f"Found {len(results)} results")

                    for res in results:
                        if count >= IMAGES_PER_CLASS:
                            break
                        img_url = res.get("image")
                        if not img_url or img_url in downloaded_urls:
                            continue
                        downloaded_urls.add(img_url)

                        try:
                            time.sleep(0.15)
                            response = requests.get(img_url, timeout=10, headers=headers)
                            if response.status_code != 200:
                                continue
                            img = Image.open(BytesIO(response.content))
                            img.verify()
                            img = Image.open(BytesIO(response.content)).convert("RGB")
                            if img.width < 250 or img.height < 250:
                                continue

                            filename = f"{category}_new_{count + 1:04d}.jpg"
                            filepath = os.path.join(save_dir, filename)
                            img.save(filepath, "JPEG", quality=92)
                            count += 1
                            print(f"[{count}/{IMAGES_PER_CLASS}] Saved {filename}")
                        except Exception:
                            continue
                    break
                except Exception as e:
                    retries += 1
                    wait = retries * 8
                    print(f"Search failed ({e}). Retrying in {wait}s ({retries}/{max_retries})")
                    time.sleep(wait)

            time.sleep(1.5)

        print(f"\nFinished {category}: {count} images downloaded")


if __name__ == "__main__":
    download_images()
