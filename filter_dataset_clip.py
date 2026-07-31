"""Flag and remove non-product images (ads, diagrams, screenshots, etc.)
from the Brain 1 training dataset using CLIP zero-shot classification.

For each category folder under `dataset/{train,val,test}/<category>/`,
builds two prompt-ensemble prototype embeddings:
  - a "real product photo" prototype, specific to that category
  - a generic "junk" prototype (ad, diagram, screenshot, watermark/collage)

Each image is compared against both prototypes; if it scores closer to
the junk prototype, it is MOVED (not deleted) to a mirrored folder under
`dataset_flagged/<split>/<category>/`, so it no longer sits in the
training dataset but nothing is lost. A CSV manifest of every decision
(scores included) is written to `dataset_flagged/manifest.csv` for review.

Run:
    python filter_dataset_clip.py
"""

import csv
import shutil
from pathlib import Path

import open_clip
import torch
from PIL import Image

DATASET_ROOT = Path("dataset")
FLAGGED_ROOT = Path("dataset_flagged")
SPLITS = ("train", "val", "test")

#: OpenAI's ViT-B-32 checkpoint was trained with QuickGELU activation;
#: open_clip's plain "ViT-B-32" config defaults to standard GELU, which
#: silently degrades embedding quality against these weights.
MODEL_NAME = "ViT-B-32-quickgelu"
PRETRAINED = "openai"
BATCH_SIZE = 32
IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".webp", ".bmp"}

#: Generic junk classes, shared across every category. Expanded from an
#: initial pass's manual spot-check, which found these specific failure
#: modes slipping through as false negatives: broken-image placeholder
#: icons, multi-product catalog collages, stylized marketing/blog
#: thumbnails with bold text, home-appliance lookalikes (e.g. HVAC
#: filters vs. car air filters), and labeled cutaway diagrams.
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
]

#: Require the positive score to beat the junk score by at least this
#: much; near-ties are treated as junk rather than trusting a razor-thin
#: win (initial pass found real misses with positive margins as high as
#: ~0.02).
MARGIN = 0.01


def category_display_name(category: str) -> str:
    """`"power_steering_pump"` -> `"power steering pump"`."""
    return category.replace("_", " ")


def positive_prompts(category: str) -> list[str]:
    """Prompt ensemble describing a genuine product photo of `category`."""
    name = category_display_name(category)
    return [
        f"a product photo of a car {name}",
        f"a close-up photograph of a {name}, an automotive spare part",
        f"a real photograph of a single {name} on a plain background",
        f"a used or new {name} auto part, isolated on white background",
    ]


def build_prototype(model, tokenizer, device, prompts: list[str]) -> torch.Tensor:
    """Average + re-normalize the text embeddings of a prompt ensemble."""
    tokens = tokenizer(prompts).to(device)
    with torch.no_grad():
        embeddings = model.encode_text(tokens)
        embeddings = embeddings / embeddings.norm(dim=-1, keepdim=True)
        prototype = embeddings.mean(dim=0)
        prototype = prototype / prototype.norm()
    return prototype


def load_batch(paths: list[Path], preprocess) -> tuple[torch.Tensor, list[Path]]:
    """Load + preprocess a batch of images, skipping unreadable files."""
    tensors = []
    kept_paths = []
    for path in paths:
        try:
            with Image.open(path) as im:
                tensors.append(preprocess(im.convert("RGB")))
            kept_paths.append(path)
        except Exception as exc:  # noqa: BLE001
            print(f"    [skip] {path.name}: unreadable ({type(exc).__name__}: {exc})")
    if not tensors:
        return torch.empty(0), []
    return torch.stack(tensors), kept_paths


def main() -> None:
    device = "cuda" if torch.cuda.is_available() else "cpu"
    print(f"Loading OpenCLIP {MODEL_NAME}/{PRETRAINED} on {device}...")
    model, _, preprocess = open_clip.create_model_and_transforms(MODEL_NAME, pretrained=PRETRAINED)
    model = model.to(device).eval()
    tokenizer = open_clip.get_tokenizer(MODEL_NAME)

    junk_prototype = build_prototype(model, tokenizer, device, JUNK_PROMPTS)

    manifest_rows = []
    totals = {"kept": 0, "flagged": 0, "unreadable": 0}

    for split in SPLITS:
        split_dir = DATASET_ROOT / split
        if not split_dir.is_dir():
            continue

        categories = sorted(p.name for p in split_dir.iterdir() if p.is_dir())
        for category in categories:
            cat_dir = split_dir / category
            image_paths = sorted(
                p for p in cat_dir.iterdir() if p.suffix.lower() in IMAGE_EXTS
            )
            if not image_paths:
                continue

            positive_prototype = build_prototype(
                model, tokenizer, device, positive_prompts(category)
            )

            print(f"\n[{split}/{category}] {len(image_paths)} images")
            flagged_count = 0

            for start in range(0, len(image_paths), BATCH_SIZE):
                batch_paths = image_paths[start : start + BATCH_SIZE]
                batch, kept_paths = load_batch(batch_paths, preprocess)
                totals["unreadable"] += len(batch_paths) - len(kept_paths)
                if batch.numel() == 0:
                    continue

                with torch.no_grad():
                    image_embeds = model.encode_image(batch.to(device))
                    image_embeds = image_embeds / image_embeds.norm(dim=-1, keepdim=True)
                    positive_scores = (image_embeds @ positive_prototype).tolist()
                    junk_scores = (image_embeds @ junk_prototype).tolist()

                for path, pos_score, junk_score in zip(kept_paths, positive_scores, junk_scores):
                    is_junk = junk_score > pos_score - MARGIN
                    manifest_rows.append(
                        {
                            "split": split,
                            "category": category,
                            "filename": path.name,
                            "positive_score": f"{pos_score:.4f}",
                            "junk_score": f"{junk_score:.4f}",
                            "flagged": is_junk,
                        }
                    )
                    if is_junk:
                        dest_dir = FLAGGED_ROOT / split / category
                        dest_dir.mkdir(parents=True, exist_ok=True)
                        shutil.move(str(path), str(dest_dir / path.name))
                        flagged_count += 1
                        totals["flagged"] += 1
                    else:
                        totals["kept"] += 1

            print(f"  -> flagged {flagged_count}/{len(image_paths)}")

    FLAGGED_ROOT.mkdir(parents=True, exist_ok=True)
    manifest_path = FLAGGED_ROOT / "manifest.csv"
    with manifest_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(
            f, fieldnames=["split", "category", "filename", "positive_score", "junk_score", "flagged"]
        )
        writer.writeheader()
        writer.writerows(manifest_rows)

    print("\n=== Summary ===")
    print(f"Kept:       {totals['kept']}")
    print(f"Flagged:    {totals['flagged']}")
    print(f"Unreadable: {totals['unreadable']}")
    print(f"Manifest written to {manifest_path}")


if __name__ == "__main__":
    main()
