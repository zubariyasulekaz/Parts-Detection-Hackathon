"""Fine-tune DINOv2 on RigidHitch's own parts.

Every accuracy figure so far comes from DINOv2 used exactly as Meta shipped it,
and the published evidence says that is the ceiling rather than the floor. In
nyris's benchmark, off-the-shelf DINOv3 scores 26.4 R@1 on a fine-grained
fastener catalogue while their domain-trained model scores 63.4 on the same
images. Nine general-purpose models were tested and all were weak at telling
near-identical industrial parts apart. Swapping to another ready-made model is
therefore not the fix; training the one we have is.

**Training signal, for free.** Two photographs of the same SKU are a positive
pair, and the SKU folders already encode that - no labelling required. The model
learns to pull a product's own photos together and push different products
apart, which is exactly the "same physical object?" question search asks.

**ArcFace rather than a plain classifier.** A softmax classifier optimises for
"which of these N SKUs", which is not what we need - the catalogue grows, and at
query time we compare embeddings, not class scores. ArcFace enforces an angular
margin between classes, so the embedding space itself becomes discriminative and
a new product slots into it without retraining.

**Augmentation does the domain-gap work.** The catalogue is studio photography
on white; a customer's photo is a workbench under a fluorescent tube. Crops,
colour jitter, blur, perspective and grey backgrounds are what stop the model
learning "a RigidHitch product is an object on clean white".

**The split is load-bearing.** Training touches the tuning half only, so
``--query-split test`` measures products the model has never seen. Scoring a
fine-tune on its own training SKUs reports memorisation, which looks spectacular
and does not survive the next new product.

Writes a plain HuggingFace directory, so nothing downstream changes - the
backend resolver already treats any name containing "/" as a model id, and a
local directory qualifies:

    python scripts/rigidhitch_embed_images.py --backend out/rigidhitch-dinov2

It is still recorded as the "dinov2" backend, so the index metadata, whitening
and search paths are untouched.

Run (Colab, GPU):
    python scripts/rigidhitch_finetune.py --images images_518 --epochs 12
"""

import argparse
import json

import random
import sys
from collections import defaultdict
from pathlib import Path

import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F
from PIL import Image
from torch.utils.data import DataLoader, Dataset

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

DEFAULT_BUILD_DIR = Path("index_build")
MODEL_ID = "facebook/dinov2-base"
IMAGE_SIZE = 224


class SkuPhotos(Dataset):
    """Every training photo, labelled by the product it belongs to."""

    def __init__(self, items: list[tuple[Path, int]], train: bool, mean, std) -> None:
        from torchvision import transforms

        self._items = items
        if train:
            self._tf = transforms.Compose([
                # Scale down to 0.5 so the model sees partial views: a customer
                # rarely frames a part the way a studio does.
                transforms.RandomResizedCrop(IMAGE_SIZE, scale=(0.5, 1.0), ratio=(0.75, 1.33)),
                transforms.RandomHorizontalFlip(),
                transforms.RandomApply([transforms.RandomRotation(15)], p=0.4),
                transforms.RandomApply([transforms.RandomPerspective(0.3, p=1.0)], p=0.3),
                # Colour and sharpness: fluorescent light, phone white balance,
                # and camera shake, none of which occur in the catalogue.
                transforms.RandomApply([transforms.ColorJitter(0.4, 0.4, 0.4, 0.1)], p=0.8),
                transforms.RandomGrayscale(p=0.1),
                transforms.RandomApply([transforms.GaussianBlur(5, (0.1, 2.0))], p=0.3),
                transforms.ToTensor(),
                transforms.Normalize(mean, std),
                # Occlusion - a hand, a shadow, another part in the way.
                transforms.RandomErasing(p=0.25, scale=(0.02, 0.15)),
            ])
        else:
            self._tf = transforms.Compose([
                transforms.Resize(IMAGE_SIZE),
                transforms.CenterCrop(IMAGE_SIZE),
                transforms.ToTensor(),
                transforms.Normalize(mean, std),
            ])

    def __len__(self) -> int:
        return len(self._items)

    def __getitem__(self, index: int):
        path, label = self._items[index]
        with Image.open(path) as handle:
            image = handle.convert("RGB")
        return self._tf(image), label


class ArcFace(nn.Module):
    """Angular-margin head.

    Cosine similarity between an embedding and each class centre, with a margin
    subtracted from the true class's angle before softmax. The margin forces the
    model to separate classes by more than "just barely correct", which is what
    makes the embedding space itself useful for retrieval rather than only the
    classifier on top of it.
    """

    def __init__(self, dim: int, classes: int, scale: float = 30.0, margin: float = 0.3) -> None:
        super().__init__()
        self.weight = nn.Parameter(torch.empty(classes, dim))
        nn.init.xavier_normal_(self.weight)
        self.scale, self.margin = scale, margin

    def forward(self, features: torch.Tensor, labels: torch.Tensor) -> torch.Tensor:
        cosine = F.linear(F.normalize(features), F.normalize(self.weight)).clamp(-1 + 1e-7, 1 - 1e-7)
        theta = torch.acos(cosine)
        target = torch.zeros_like(cosine)
        target.scatter_(1, labels.view(-1, 1), 1.0)
        # Margin applied only to the true class, then everything rescaled.
        logits = torch.cos(theta + self.margin * target) * self.scale
        return F.cross_entropy(logits, labels)


def build_items(build_dir: Path, images: Path, max_skus_per_hash: int,
                min_photos: int, limit_skus: int | None = None):
    """Training photos from the tuning split only, after the same de-dup filter.

    Filtering to match the shipped index matters: training on photos that the
    index will never contain teaches the model to separate images nobody can
    search for, and shared placeholder photos actively teach it that unrelated
    products look identical.
    """
    rows = [json.loads(line) for line in
            (build_dir / "embed_rows.jsonl").open(encoding="utf-8") if line.strip()]
    split = json.loads((build_dir / "split.json").read_text(encoding="utf-8"))
    tuning = set(split["tuning_skus"])

    by_sku: dict[str, list[Path]] = defaultdict(list)
    for row in rows:
        if row["n_skus_sharing"] > max_skus_per_hash or row["sku"] not in tuning:
            continue
        path = images / row["rel"]
        if path.is_file():
            by_sku[row["sku"]].append(path)

    # A single-photo SKU gives ArcFace a class it cannot learn to separate from
    # anything - there is no within-class variation to model.
    usable = {sku: paths for sku, paths in by_sku.items() if len(paths) >= min_photos}
    if limit_skus is not None:
        usable = {sku: usable[sku] for sku in sorted(usable)[:limit_skus]}
    labels = {sku: i for i, sku in enumerate(sorted(usable))}
    return [(p, labels[sku]) for sku, paths in usable.items() for p in paths], len(labels)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--build-dir", type=Path, default=DEFAULT_BUILD_DIR)
    parser.add_argument("--images", type=Path, required=True,
                        help="Root holding one folder per SKU (the 518px set).")
    parser.add_argument("--out", type=Path, default=Path("out/rigidhitch-dinov2"))
    parser.add_argument("--model-id", default=MODEL_ID)
    parser.add_argument("--epochs", type=int, default=12)
    parser.add_argument("--batch-size", type=int, default=32)
    parser.add_argument("--lr-backbone", type=float, default=1e-5,
                        help="Deliberately small: DINOv2's features are already good, and a "
                             "large step erases the pretraining that makes it work at all.")
    parser.add_argument("--lr-head", type=float, default=1e-3)
    parser.add_argument("--min-photos", type=int, default=2)
    parser.add_argument("--max-skus-per-hash", type=int, default=1)
    parser.add_argument("--workers", type=int, default=2)
    parser.add_argument("--limit-skus", type=int, default=None,
                        help="Train on this many products only. For verifying the run starts "
                             "and the loss falls before committing an hour of GPU to it.")
    parser.add_argument("--seed", type=int, default=20260829)
    args = parser.parse_args()

    torch.manual_seed(args.seed)
    random.seed(args.seed)
    np.random.seed(args.seed)

    from transformers import AutoImageProcessor, AutoModel

    device = "cuda" if torch.cuda.is_available() else "cpu"
    if device == "cpu":
        print("WARNING: no GPU found. This will take many hours - run it in Colab.")

    processor = AutoImageProcessor.from_pretrained(args.model_id)
    mean, std = processor.image_mean, processor.image_std

    items, n_classes = build_items(args.build_dir, args.images, args.max_skus_per_hash,
                                   args.min_photos, args.limit_skus)
    if n_classes < 2:
        raise SystemExit("not enough tuning SKUs with multiple photos to train on")
    print(f"training on {len(items):,} photos across {n_classes:,} products "
          f"(tuning split only; the test half is never seen)")

    loader = DataLoader(
        SkuPhotos(items, train=True, mean=mean, std=std),
        batch_size=args.batch_size, shuffle=True, num_workers=args.workers,
        pin_memory=(device == "cuda"), drop_last=True,
    )

    model = AutoModel.from_pretrained(args.model_id).to(device)
    dim = model.config.hidden_size
    head = ArcFace(dim, n_classes).to(device)

    optimizer = torch.optim.AdamW([
        {"params": model.parameters(), "lr": args.lr_backbone},
        {"params": head.parameters(), "lr": args.lr_head},
    ], weight_decay=0.05)
    steps = max(1, args.epochs * len(loader))
    schedule = torch.optim.lr_scheduler.OneCycleLR(
        optimizer, max_lr=[args.lr_backbone, args.lr_head], total_steps=steps, pct_start=0.1)
    scaler = torch.amp.GradScaler(device, enabled=(device == "cuda"))

    for epoch in range(1, args.epochs + 1):
        model.train()
        total, seen, correct = 0.0, 0, 0
        for images, labels in loader:
            images, labels = images.to(device, non_blocking=True), labels.to(device)
            optimizer.zero_grad(set_to_none=True)
            with torch.amp.autocast(device, enabled=(device == "cuda")):
                out = model(pixel_values=images)
                # pooler_output is what the runtime embeds with, so it is what
                # must be trained - training a different pooling would improve a
                # vector nothing ever uses.
                features = getattr(out, "pooler_output", None)
                if features is None:
                    features = out.last_hidden_state[:, 0]
                loss = head(features.float(), labels)
            scaler.scale(loss).backward()
            scaler.unscale_(optimizer)
            torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
            scaler.step(optimizer)
            scaler.update()
            schedule.step()

            total += loss.item() * labels.size(0)
            seen += labels.size(0)
            with torch.no_grad():
                cosine = F.linear(F.normalize(features.float()), F.normalize(head.weight))
                correct += (cosine.argmax(1) == labels).sum().item()
        print(f"epoch {epoch:>2}/{args.epochs}  loss {total / max(seen, 1):.4f}  "
              f"train-acc {100 * correct / max(seen, 1):.1f}%", flush=True)

    args.out.mkdir(parents=True, exist_ok=True)
    model.save_pretrained(args.out)
    processor.save_pretrained(args.out)
    # Recorded so a later run cannot silently disagree about what was held out.
    (args.out / "finetune.json").write_text(json.dumps({
        "base_model": args.model_id,
        "photos": len(items),
        "classes": n_classes,
        "epochs": args.epochs,
        "trained_on": "tuning split only",
        "seed": args.seed,
    }, indent=2))
    print(f"\nSaved to {args.out}")
    print("Re-embed with it, rebuild, then compare against the baseline using")
    print("  --query-split test   (products the model never trained on)")


if __name__ == "__main__":
    main()
