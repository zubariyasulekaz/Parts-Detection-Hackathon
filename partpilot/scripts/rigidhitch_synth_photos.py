"""Make catalogue photographs look like photographs a customer would send.

Every product image RigidHitch has is a studio shot: the part centred on white,
evenly lit, filling the frame. Every photograph a customer sends is the
opposite - the part on gravel or a truck bed, small, tilted, in whatever light
was there. Measured on 20 products, that difference is the whole problem: a
part filling the frame matches its own product 95% of the time, and the same
part shrunk into a busy frame matches 0%.

The model has never been shown the second kind of picture, so this makes them:
cut the part out of its white background, drop it onto a real surface, and put
it through what a phone camera does to an image.

**Compositing, not generation.** A diffusion model would produce something more
convincingly photographic, and would also redraw the part - subtly changing a
drop height, a hole spacing, a bracket angle. Those details are exactly what
separates one SKU from the next, so a generated image can teach the model that
a 6 inch drop looks like a 7 inch one. Here the pixels of the part are the
original pixels; only its surroundings and the camera change.

**Backgrounds come from real photographs.** Review photos of parts installed on
trucks and driveways are useless for testing - the product is incidental and
unlabelled - but their backgrounds are exactly the surfaces we need, shot on
real phones in real light.

Run:
    python scripts/rigidhitch_synth_photos.py --skus 10 --per-photo 6
"""

import argparse
import json
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from PIL import Image, ImageEnhance, ImageFilter  # noqa: E402

DEFAULT_BUILD = Path(r"C:\Users\Vasuki.KLIZER-49\Downloads\rigidhitch_dataset\rigidhitch_dataset\index_build")
DEFAULT_IMAGES = Path(r"C:\Users\Vasuki.KLIZER-49\Downloads\images_clean\images_clean")
DEFAULT_BACKGROUNDS = Path(r"C:\Users\Vasuki.KLIZER-49\Downloads\real photos")
IMAGE_TYPES = {".jpg", ".jpeg", ".png", ".webp"}
OUTPUT_SIZE = 640


def load_backgrounds(folder: Path, size: int, limit: int = 60) -> list[Image.Image]:
    """Close crops of real surfaces, taken from photographs of anything.

    Only texture and lighting matter, so what the photograph was *of* is
    irrelevant - a review photo of a tonneau cover supplies a perfectly good
    truck bed. But it has to be a *surface*: full-frame crops gave whole
    vehicles and skylines, and a part composited onto those floats in mid-air
    rather than resting on anything.

    Two rules keep them surfaces. Crops are small and enlarged, so a scene
    becomes one texture within it; and they come from the lower half, where
    ground, floor and bumper live rather than sky and roofline.
    """
    files = sorted(p for p in folder.rglob("*") if p.suffix.lower() in IMAGE_TYPES)
    backgrounds: list[Image.Image] = []
    for path in files[:limit]:
        try:
            with Image.open(path) as handle:
                image = handle.convert("RGB")
        except Exception:  # noqa: BLE001 - a corrupt download is not fatal
            continue
        side = min(image.width, image.height) // 2
        if side < 120:
            continue
        floor = image.height // 2  # lower half only
        for left in (0, max(0, image.width - side)):
            top = min(floor, image.height - side)
            crop = image.crop((left, top, left + side, top + side)).resize((size, size))
            backgrounds.append(crop)
    return backgrounds


def cut_out(path: Path):
    """The part with its background removed, as RGBA, cropped to its own bounds."""
    from rembg import remove  # noqa: PLC0415

    with Image.open(path) as handle:
        original = handle.convert("RGB")
    cut = remove(original)
    box = cut.split()[-1].point(lambda v: 255 if v > 24 else 0).getbbox()
    if not box:
        return None
    return cut.crop(box)


def compose(part: Image.Image, background: Image.Image, rng: random.Random) -> Image.Image:
    """One synthetic photograph: the part somewhere in a real scene."""
    scene = background.copy()
    size = scene.width

    # Scale so the part occupies a plausible share of the frame. A customer
    # standing over a part on the ground fills far less of the picture than a
    # product photographer does, and the low end is where the model currently
    # fails completely.
    target = rng.uniform(0.18, 0.62) * size
    ratio = target / max(part.width, part.height)
    piece = part.resize((max(1, int(part.width * ratio)), max(1, int(part.height * ratio))))
    piece = piece.rotate(rng.uniform(-28, 28), expand=True, resample=Image.BICUBIC)

    left = rng.randint(0, max(0, size - piece.width))
    # Kept in the lower part of the frame: things photographed lying about rest
    # on something, and a part pasted into the top of a picture reads as
    # floating, which teaches the model to look for cut-out edges rather than
    # for the part.
    lowest = max(0, size - piece.height)
    top = rng.randint(int(lowest * 0.35), lowest) if lowest else 0

    # A shadow, so the part sits on the surface instead of floating on it. Just
    # the silhouette, blurred and offset - crude, but the alternative reads as
    # a sticker and teaches the model that parts have hard cut edges.
    shadow = Image.new("RGBA", piece.size, (0, 0, 0, 0))
    shadow.paste((0, 0, 0, rng.randint(70, 130)), (0, 0), piece.split()[-1])
    shadow = shadow.filter(ImageFilter.GaussianBlur(max(2, piece.width // 22)))
    offset = max(2, piece.width // 26)
    scene.paste(shadow, (left + offset, top + offset), shadow)
    scene.paste(piece, (left, top), piece)

    # What the camera and the light do to the whole frame, applied after the
    # paste so the part and its surroundings share them - a part that is
    # sharper or better lit than the scene around it is a giveaway.
    scene = ImageEnhance.Brightness(scene).enhance(rng.uniform(0.62, 1.24))
    scene = ImageEnhance.Contrast(scene).enhance(rng.uniform(0.78, 1.20))
    scene = ImageEnhance.Color(scene).enhance(rng.uniform(0.65, 1.30))
    if rng.random() < 0.55:
        scene = scene.filter(ImageFilter.GaussianBlur(rng.uniform(0.4, 1.5)))
    return scene


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--build-dir", type=Path, default=DEFAULT_BUILD)
    parser.add_argument("--images", type=Path, default=DEFAULT_IMAGES)
    parser.add_argument("--backgrounds", type=Path, default=DEFAULT_BACKGROUNDS)
    parser.add_argument("--out", type=Path, default=Path("synthetic"))
    parser.add_argument("--skus", type=int, default=10)
    parser.add_argument("--per-photo", type=int, default=6,
                        help="Synthetic photographs generated from each catalogue image.")
    parser.add_argument("--start", type=int, default=0,
                        help="Skip this many SKUs first, so two people can split the list.")
    parser.add_argument("--seed", type=int, default=20260831)
    args = parser.parse_args()

    rng = random.Random(args.seed + args.start)
    backgrounds = load_backgrounds(args.backgrounds, OUTPUT_SIZE)
    if not backgrounds:
        raise SystemExit(f"no usable background photographs in {args.backgrounds}")
    print(f"{len(backgrounds)} background crops from {args.backgrounds.name}")

    rows = [json.loads(l) for l in (args.build_dir / "embed_rows.jsonl").open(encoding="utf-8") if l.strip()]
    by_sku: dict[str, list[Path]] = {}
    for row in rows:
        if row["n_skus_sharing"] > 1:
            continue
        path = args.images / row["rel"]
        if path.is_file():
            by_sku.setdefault(row["sku"], []).append(path)

    chosen = sorted(by_sku)[args.start:args.start + args.skus]
    args.out.mkdir(parents=True, exist_ok=True)
    made = 0
    for n, sku in enumerate(chosen, 1):
        folder = args.out / sku
        folder.mkdir(exist_ok=True)
        for source in by_sku[sku]:
            part = cut_out(source)
            if part is None:
                print(f"  {sku}: no subject found in {source.name}, skipped")
                continue
            for variant in range(args.per_photo):
                scene = compose(part, rng.choice(backgrounds), rng)
                scene.save(folder / f"{source.stem}-synth{variant + 1}.jpg", quality=88)
                made += 1
        print(f"  [{n}/{len(chosen)}] {sku}: {len(by_sku[sku])} photo(s) -> "
              f"{len(by_sku[sku]) * args.per_photo} synthetic", flush=True)

    print(f"\n{made:,} synthetic photographs across {len(chosen)} SKUs -> {args.out.resolve()}")
    print("Look at them before training on them: if they do not read as phone")
    print("photographs to you, they will not teach the model what one looks like.")


if __name__ == "__main__":
    main()
