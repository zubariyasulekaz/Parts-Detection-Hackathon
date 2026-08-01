"""Try VLM re-ranking on top of Brain 2 and measure whether it actually helps.

Brain 2 gets the right SKU into its top 3 about 93% of the time but only ranks
it first about 69% of the time. The idea here is to hand Brain 2's shortlist to
a vision-language model and let it look at the pictures and choose, instead of
trusting the raw similarity ordering.

This is a measurement script, not a feature. It reports:

    fixes   - FAISS was wrong, the VLM got it right
    breaks  - FAISS was right, the VLM got it wrong
    net     - the accuracy change once both are counted

Only counting fixes would flatter the result, so both are reported.

Retrieval is leave-one-out, exactly like ``evaluate_brain2.py``: the query image
is excluded from its own product's fingerprint. Embeddings are cached to disk so
a second run skips straight to the VLM part.

Run (GPU strongly recommended - the VLM is slow on CPU):

    # the three weakest categories, ~73 queries
    python scripts/test_vlm_rerank.py --remove-bg \
        --categories "Brake Pads,Exhaust Manifold,Wheel Hub Assembly"

    # everything
    python scripts/test_vlm_rerank.py --remove-bg
"""

import argparse
import csv
import sys
from collections import defaultdict
from pathlib import Path

import numpy as np
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from backend.config.paths import DATASETS_DIR  # noqa: E402
from backend.pipeline.brain2_similarity.embedding_generator import EmbeddingGenerator  # noqa: E402
from backend.utils.image_utils import remove_background  # noqa: E402

IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".webp"}
CACHE = Path(__file__).resolve().parent.parent / "backend" / "data" / "embeddings" / "eval_cache.npz"


def unit(v: np.ndarray) -> np.ndarray:
    n = np.linalg.norm(v)
    return v / n if n else v


def load_catalog() -> list[dict[str, str]]:
    path = DATASETS_DIR / "catalog.csv"
    with path.open(newline="", encoding="utf-8-sig") as f:
        return [r for r in csv.DictReader(f) if (r.get("sku") or "").strip()]


def collect_images(records, categories):
    """sku -> (category, [image paths]) for the categories we care about."""
    out = {}
    for r in records:
        category = (r.get("category") or "").strip()
        if not category or (categories and category not in categories):
            continue
        folder = DATASETS_DIR / (r.get("image_folder") or f"images/{r['sku']}")
        if not folder.is_dir():
            continue
        paths = sorted(p for p in folder.iterdir() if p.suffix.lower() in IMAGE_EXTS)
        if len(paths) >= 2:  # leave-one-out needs at least two
            out[r["sku"]] = (category, paths)
    return out


def embed_all(images_by_sku, remove_bg, use_cache=True):
    """Embed every image once. Cached so repeat runs skip the slow part."""
    key_for = lambda sku, p: f"{sku}|{p.name}"  # noqa: E731
    cached = {}
    if use_cache and CACHE.exists():
        with np.load(CACHE) as z:
            cached = {k: z[k] for k in z.files}
        print(f"Loaded {len(cached)} cached embeddings from {CACHE.name}")

    generator = None
    vectors: dict[str, list[np.ndarray]] = defaultdict(list)
    fresh = {}
    for sku, (_category, paths) in images_by_sku.items():
        for p in paths:
            k = key_for(sku, p)
            if k in cached:
                vectors[sku].append(cached[k])
                continue
            if generator is None:
                generator = EmbeddingGenerator()
            with Image.open(p) as im:
                im = im.convert("RGB")
                if remove_bg:
                    im = remove_background(im)
                v = unit(np.asarray(generator.generate(im), dtype=np.float32))
            vectors[sku].append(v)
            fresh[k] = v
            print(f"  embedded {sku}/{p.name}")

    if fresh:
        CACHE.parent.mkdir(parents=True, exist_ok=True)
        np.savez(CACHE, **{**cached, **fresh})
        print(f"Cached {len(fresh)} new embeddings -> {CACHE.name}")
    return vectors


class Reranker:
    """Asks a vision-language model which candidate matches the query image."""

    def __init__(self, model_name: str) -> None:
        import torch
        from transformers import AutoProcessor, AutoModelForImageTextToText

        self._torch = torch
        print(f"Loading VLM: {model_name} ...")
        self._processor = AutoProcessor.from_pretrained(model_name)
        self._model = AutoModelForImageTextToText.from_pretrained(
            model_name,
            torch_dtype=torch.float16 if torch.cuda.is_available() else torch.float32,
            device_map="auto" if torch.cuda.is_available() else None,
        )
        self._model.eval()
        if not torch.cuda.is_available():
            print("  [warn] no GPU detected - this will be very slow")

    def choose(self, query: Image.Image, candidates: list[Image.Image]) -> int | None:
        """Return the index of the chosen candidate, or None if unparseable."""
        listing = "\n".join(f"{i + 1}. candidate image {i + 1}" for i in range(len(candidates)))
        prompt = (
            "The first image is a photo of a car part a customer wants to identify.\n"
            f"The next {len(candidates)} images are catalog products it might be:\n{listing}\n\n"
            "Which candidate is the SAME product as the first image? Compare shape, "
            "packaging, colour, markings and any visible text or part numbers.\n"
            f"Reply with only the number (1-{len(candidates)})."
        )
        content = [{"type": "image", "image": query}]
        content += [{"type": "image", "image": c} for c in candidates]
        content.append({"type": "text", "text": prompt})
        messages = [{"role": "user", "content": content}]

        inputs = self._processor.apply_chat_template(
            messages, add_generation_prompt=True, tokenize=True,
            return_dict=True, return_tensors="pt",
        ).to(self._model.device)

        with self._torch.inference_mode():
            out = self._model.generate(**inputs, max_new_tokens=8, do_sample=False)
        reply = self._processor.decode(
            out[0][inputs["input_ids"].shape[-1]:], skip_special_tokens=True
        )
        for token in reply.strip().split():
            digits = "".join(ch for ch in token if ch.isdigit())
            if digits:
                idx = int(digits) - 1
                if 0 <= idx < len(candidates):
                    return idx
        return None


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--remove-bg", action="store_true",
                    help="Background-remove images (match how the index was built).")
    ap.add_argument("--categories", default="",
                    help="Comma-separated categories to test. Default: all.")
    ap.add_argument("--top-k", type=int, default=5,
                    help="How many candidates to hand the VLM (default 5).")
    ap.add_argument("--vlm-model", default="Qwen/Qwen2.5-VL-3B-Instruct",
                    help="Any image-text-to-text model, e.g. google/gemma-3-4b-it.")
    ap.add_argument("--limit", type=int, default=0,
                    help="Stop after N queries (quick smoke test).")
    args = ap.parse_args()

    categories = {c.strip() for c in args.categories.split(",") if c.strip()}
    records = load_catalog()
    images_by_sku = collect_images(records, categories)
    if not images_by_sku:
        raise SystemExit("No products matched - check --categories spelling.")

    by_category: dict[str, list[str]] = defaultdict(list)
    for sku, (category, _paths) in images_by_sku.items():
        by_category[category].append(sku)
    print(f"Testing {len(images_by_sku)} products across {len(by_category)} categories\n")

    vectors = embed_all(images_by_sku, args.remove_bg)
    reranker = Reranker(args.vlm_model)

    fixes = breaks = both_right = both_wrong = unparsed = 0
    faiss_hits = vlm_hits = total = 0
    examples: list[str] = []

    for category, skus in sorted(by_category.items()):
        full = {s: unit(np.mean(np.stack(vectors[s]), axis=0)) for s in skus}
        for true_sku in skus:
            _cat, paths = images_by_sku[true_sku]
            for i, query_vec in enumerate(vectors[true_sku]):
                if args.limit and total >= args.limit:
                    break
                # leave-one-out: rebuild the true product without this image
                held = [v for j, v in enumerate(vectors[true_sku]) if j != i]
                loo = unit(np.mean(np.stack(held), axis=0))

                scored = sorted(
                    ((s, float(np.dot(query_vec, loo if s == true_sku else full[s]))) for s in skus),
                    key=lambda x: -x[1],
                )
                shortlist = [s for s, _ in scored[: args.top_k]]
                faiss_pick = shortlist[0]

                # the VLM sees the query photo and one photo per candidate
                query_img = Image.open(paths[i]).convert("RGB")
                cand_imgs = []
                for s in shortlist:
                    _c, cand_paths = images_by_sku[s]
                    # never show the query image itself as a candidate
                    pick = next((p for p in cand_paths if p != paths[i]), cand_paths[0])
                    cand_imgs.append(Image.open(pick).convert("RGB"))

                choice = reranker.choose(query_img, cand_imgs)
                if choice is None:
                    unparsed += 1
                    vlm_pick = faiss_pick          # fall back to FAISS
                else:
                    vlm_pick = shortlist[choice]

                total += 1
                f_ok = faiss_pick == true_sku
                v_ok = vlm_pick == true_sku
                faiss_hits += f_ok
                vlm_hits += v_ok
                if f_ok and v_ok:
                    both_right += 1
                elif not f_ok and v_ok:
                    fixes += 1
                    examples.append(f"  FIXED  {true_sku} img{i+1}: {faiss_pick} -> {vlm_pick}")
                elif f_ok and not v_ok:
                    breaks += 1
                    examples.append(f"  BROKE  {true_sku} img{i+1}: {faiss_pick} -> {vlm_pick}")
                else:
                    both_wrong += 1

                if total % 10 == 0:
                    print(f"  {total} queries... FAISS {faiss_hits/total:.1%} | VLM {vlm_hits/total:.1%}")

    print("\n" + "=" * 60)
    print("VLM RE-RANKING TEST")
    print("=" * 60)
    print(f"Queries tested      {total}")
    print(f"Candidates shown    top-{args.top_k}")
    print(f"VLM                 {args.vlm_model}")
    print("-" * 60)
    print(f"FAISS alone         {faiss_hits:>4} / {total}   {faiss_hits/total:>6.1%}")
    print(f"FAISS + VLM         {vlm_hits:>4} / {total}   {vlm_hits/total:>6.1%}")
    delta = (vlm_hits - faiss_hits) / total * 100
    print(f"Change              {delta:>+6.1f} percentage points")
    print("-" * 60)
    print(f"  fixed by VLM      {fixes}")
    print(f"  broken by VLM     {breaks}")
    print(f"  both right        {both_right}")
    print(f"  both wrong        {both_wrong}")
    if unparsed:
        print(f"  unreadable reply  {unparsed} (fell back to FAISS)")
    print("=" * 60)
    if delta > 2:
        print("\nWorth building into the pipeline.")
    elif delta > 0:
        print("\nMarginal - weigh the gain against the added latency.")
    else:
        print("\nNot worth it on this data.")

    if examples:
        print("\nWhat changed:")
        for line in examples[:30]:
            print(line)
        if len(examples) > 30:
            print(f"  ... and {len(examples) - 30} more")


if __name__ == "__main__":
    main()
