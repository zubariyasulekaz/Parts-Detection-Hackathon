import os
import time
import requests
from PIL import Image
from io import BytesIO
from ddgs import DDGS

queries = {
    "suspension_bushing": [
    "car suspension bushing",
    "automotive suspension bushing",
    "car suspension bushings",
    "OEM suspension bushing",
    "suspension bushing product photo",
    "suspension bushing isolated",
    "rubber suspension bushing",
    "polyurethane suspension bushing",
    "control arm bushing",
    "car control arm bushing",
    "suspension arm bushing",
    "vehicle suspension bushing",
    "suspension bushing white background",
    "replacement suspension bushing",
    "new suspension bushing",
    "Febi Bilstein suspension bushing",
    "Lemforder suspension bushing",
    "MOOG suspension bushing",
    "TRW suspension bushing",
    "Meyle suspension bushing"
]
}

IMAGES_PER_CLASS = 400


def download_images():
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    }

    for folder, search_queries in queries.items():
        print(f"\n--- Fetching images for: {folder} ---")

        save_dir = os.path.join("dataset", folder)
        os.makedirs(save_dir, exist_ok=True)

        count = len(os.listdir(save_dir))
        downloaded_urls = set()

        ddgs = DDGS()

        for search_query in search_queries:

            if count >= IMAGES_PER_CLASS:
                break

            print(f"\nSearching: {search_query}")

            retries = 0
            max_retries = 5

            while retries < max_retries:

                try:
                    results = list(
                        ddgs.images(
                            search_query,
                            max_results=100
                        )
                    )

                    print(f"Found {len(results)} results")

                    for res in results:

                        if count >= IMAGES_PER_CLASS:
                            break

                        img_url = res.get("image")

                        if not img_url:
                            continue

                        if img_url in downloaded_urls:
                            continue

                        downloaded_urls.add(img_url)

                        try:
                            time.sleep(0.2)

                            response = requests.get(
                                img_url,
                                timeout=10,
                                headers=headers,
                            )

                            if response.status_code != 200:
                                continue

                            img = Image.open(BytesIO(response.content))
                            img.verify()

                            img = Image.open(BytesIO(response.content)).convert("RGB")

                            if img.width < 300 or img.height < 300:
                                continue

                            filename = f"{folder}_{count+1:04d}.jpg"
                            filepath = os.path.join(save_dir, filename)

                            img.save(filepath, "JPEG", quality=95)

                            count += 1

                            print(f"[{count}/{IMAGES_PER_CLASS}] Saved {filename}")

                        except Exception:
                            continue

                    # Finished this search query successfully
                    break

                except Exception as e:
                    retries += 1
                    wait = retries * 10

                    print(
                        f"Search failed ({e}). Retrying in {wait}s "
                        f"({retries}/{max_retries})"
                    )

                    time.sleep(wait)

            # Small pause before next search query
            time.sleep(2)

        print(f"\nFinished {folder}: {count} images downloaded")


if __name__ == "__main__":
    download_images()