"""Diagnostic: does resizing to 320px measurably hurt class separability?

Compares CLIP-embedding k-NN accuracy on the full-resolution cleaned
dataset (`dataset/`) vs. the resized cleaned dataset (`dataset_resized/`).
Both use the SAME train/test split and SAME images (just different
resolution), so any accuracy gap is attributable to the resize itself
rather than to which images are present.

This is a fast proxy (CLIP embeddings + k-NN, not the actual EfficientNet
model) to check, in minutes rather than a full Colab retrain, whether the
resize plausibly explains a 95% -> 43% test-accuracy collapse.
"""

import random
from pathlib import Path

import numpy as np
import open_clip
import torch
from PIL import Image

IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".webp", ".bmp"}
TRAIN_PER_CLASS = 40
SEED = 0


def load_model():
    model, _, preprocess = open_clip.create_model_and_transforms(
        "ViT-B-32-quickgelu", pretrained="openai"
    )
    model = model.to("cpu").eval()
    return model, preprocess


def embed_image(model, preprocess, path: Path) -> np.ndarray:
    with Image.open(path) as im:
        tensor = preprocess(im.convert("RGB"))
    with torch.no_grad():
        emb = model.encode_image(tensor.unsqueeze(0))
        emb = emb / emb.norm(dim=-1, keepdim=True)
    return emb.squeeze(0).numpy()


def build_split(root: Path, model, preprocess, rng: random.Random):
    categories = sorted(p.name for p in (root / "train").iterdir() if p.is_dir())

    train_x, train_y = [], []
    for cat in categories:
        paths = sorted(
            p for p in (root / "train" / cat).iterdir() if p.suffix.lower() in IMAGE_EXTS
        )
        sample = rng.sample(paths, min(TRAIN_PER_CLASS, len(paths)))
        for p in sample:
            train_x.append(embed_image(model, preprocess, p))
            train_y.append(cat)

    test_x, test_y, test_paths = [], [], []
    for cat in categories:
        paths = sorted(
            p for p in (root / "test" / cat).iterdir() if p.suffix.lower() in IMAGE_EXTS
        )
        for p in paths:
            test_x.append(embed_image(model, preprocess, p))
            test_y.append(cat)
            test_paths.append(p.name)

    return np.array(train_x), train_y, np.array(test_x), test_y, test_paths


def knn_predict(train_x, train_y, query, k=5):
    sims = train_x @ query
    top_k = np.argsort(-sims)[:k]
    votes = {}
    for j in top_k:
        votes[train_y[j]] = votes.get(train_y[j], 0) + 1
    return max(votes, key=votes.get)


def evaluate(label, root: Path, model, preprocess):
    rng = random.Random(SEED)
    train_x, train_y, test_x, test_y, test_paths = build_split(root, model, preprocess, rng)
    correct = 0
    preds = []
    for i in range(len(test_x)):
        pred = knn_predict(train_x, train_y, test_x[i], k=5)
        preds.append(pred)
        if pred == test_y[i]:
            correct += 1
    acc = correct / len(test_x)
    print(f"[{label}] train={len(train_x)} test={len(test_x)} kNN accuracy={acc:.4f}")
    return acc, list(zip(test_paths, test_y, preds))


def main():
    model, preprocess = load_model()

    acc_orig, results_orig = evaluate("ORIGINAL (full-res, cleaned)", Path("dataset"), model, preprocess)
    acc_resized, results_resized = evaluate("RESIZED (320px, cleaned)", Path("dataset_resized"), model, preprocess)

    print()
    print(f"Original  kNN accuracy: {acc_orig:.4f}")
    print(f"Resized   kNN accuracy: {acc_resized:.4f}")
    print(f"Delta: {acc_orig - acc_resized:+.4f}")


if __name__ == "__main__":
    main()
