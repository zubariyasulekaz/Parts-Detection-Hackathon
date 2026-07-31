"""Clean freshly-scraped candidate images (CLIP zero-shot, same approach as
filter_dataset_clip.py) and merge survivors into dataset/{train,val,test}/<category>/
at roughly a 70/15/15 split, matching the existing dataset's ratios.

Run after scrape_more_images.py has populated staging_scrape/<category>/.
"""

import random
import shutil
from pathlib import Path

import open_clip
import torch
from PIL import Image

STAGING_DIR = Path("staging_scrape")
DATASET_ROOT = Path("dataset")
IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".webp", ".bmp"}

MODEL_NAME = "ViT-B-32-quickgelu"
PRETRAINED = "openai"
BATCH_SIZE = 32
MARGIN = 0.01
SPLIT_RATIOS = {"train": 0.70, "val": 0.15, "test": 0.15}
SEED = 0

JUNK_PROMPTS = [
    "an advertisement banner with bold marketing text and logos",
    "a marketing blog thumbnail or infographic with large bold text overlay",
    "a labeled technical diagram or cutaway illustration with callout arrows pointing to parts",
    "a computer-rendered illustration or digital artwork, not a real photograph",
    "a screenshot of a website, online store, or shopping listing",
    "a logo, brand watermark, or stock photo watermark overlay",
    "a catalog collage showing several different unrelated products together",
    "a placeholder icon for a missing or broken image, such as a shopping bag or camera outline icon",
    "a home appliance or household item such as an HVAC, furnace, or air conditioner filter, not a vehicle part",
    "a photo of an unrelated scene such as cars driving, people, or landscapes",
    "a retail packaging box, not an isolated product photo",
    "a full kit or bundle of many different parts, not a single clean part photo",
]


def category_display_name(category: str) -> str:
    return category.replace("_", " ")


def positive_prompts(category: str) -> list[str]:
    name = category_display_name(category)
    return [
        f"a product photo of a car {name}",
        f"a close-up photograph of a {name}, an automotive spare part",
        f"a real photograph of a single {name} on a plain background",
        f"a used or new {name} auto part, isolated on white background",
    ]


def build_prototype(model, tokenizer, device, prompts):
    tokens = tokenizer(prompts).to(device)
    with torch.no_grad():
        embeddings = model.encode_text(tokens)
        embeddings = embeddings / embeddings.norm(dim=-1, keepdim=True)
        prototype = embeddings.mean(dim=0)
        prototype = prototype / prototype.norm()
    return prototype


def load_batch(paths, preprocess):
    tensors, kept = [], []
    for p in paths:
        try:
            with Image.open(p) as im:
                tensors.append(preprocess(im.convert("RGB")))
            kept.append(p)
        except Exception as exc:  # noqa: BLE001
            print(f"    [skip] {p.name}: unreadable ({exc})")
    if not tensors:
        return torch.empty(0), []
    return torch.stack(tensors), kept


def clean_category(category: str, model, tokenizer, preprocess, device) -> list[Path]:
    src_dir = STAGING_DIR / category
    if not src_dir.is_dir():
        print(f"  [warn] no staging folder for {category}")
        return []

    image_paths = sorted(p for p in src_dir.iterdir() if p.suffix.lower() in IMAGE_EXTS)
    if not image_paths:
        return []

    positive_prototype = build_prototype(model, tokenizer, device, positive_prompts(category))
    junk_prototype = build_prototype(model, tokenizer, device, JUNK_PROMPTS)

    survivors = []
    for start in range(0, len(image_paths), BATCH_SIZE):
        batch_paths = image_paths[start : start + BATCH_SIZE]
        batch, kept_paths = load_batch(batch_paths, preprocess)
        if batch.numel() == 0:
            continue
        with torch.no_grad():
            image_embeds = model.encode_image(batch.to(device))
            image_embeds = image_embeds / image_embeds.norm(dim=-1, keepdim=True)
            pos_scores = (image_embeds @ positive_prototype).tolist()
            junk_scores = (image_embeds @ junk_prototype).tolist()

        for path, pos_score, junk_score in zip(kept_paths, pos_scores, junk_scores):
            is_junk = junk_score > pos_score - MARGIN
            if not is_junk:
                survivors.append(path)

    print(f"  {category}: {len(survivors)}/{len(image_paths)} survived CLIP filtering")
    return survivors


def merge_into_dataset(category: str, survivors: list[Path]) -> dict:
    rng = random.Random(SEED)
    rng.shuffle(survivors)

    n = len(survivors)
    n_train = int(n * SPLIT_RATIOS["train"])
    n_val = int(n * SPLIT_RATIOS["val"])
    buckets = {
        "train": survivors[:n_train],
        "val": survivors[n_train : n_train + n_val],
        "test": survivors[n_train + n_val :],
    }

    counts = {}
    for split, paths in buckets.items():
        dest_dir = DATASET_ROOT / split / category
        dest_dir.mkdir(parents=True, exist_ok=True)
        for p in paths:
            shutil.copy2(p, dest_dir / p.name)
        counts[split] = len(paths)
    return counts


def main():
    device = "cuda" if torch.cuda.is_available() else "cpu"
    print(f"Loading OpenCLIP {MODEL_NAME}/{PRETRAINED} on {device}...")
    model, _, preprocess = open_clip.create_model_and_transforms(MODEL_NAME, pretrained=PRETRAINED)
    model = model.to(device).eval()
    tokenizer = open_clip.get_tokenizer(MODEL_NAME)

    categories = sorted(p.name for p in STAGING_DIR.iterdir() if p.is_dir())
    for category in categories:
        print(f"\n=== {category} ===")
        survivors = clean_category(category, model, tokenizer, preprocess, device)
        counts = merge_into_dataset(category, survivors)
        print(f"  merged: {counts}")


if __name__ == "__main__":
    main()
