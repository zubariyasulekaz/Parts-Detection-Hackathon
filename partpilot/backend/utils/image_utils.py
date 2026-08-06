"""Generic image I/O helpers.

Only basic decode/encode plumbing lives here. Model-specific
pre-processing (resizing, normalization, background removal) belongs in
`backend.pipeline.brain1_classifier.preprocess` / the Brain 2 embedding
pipeline instead, since that logic is model-dependent.
"""

import base64
import io

from PIL import Image, UnidentifiedImageError

from backend.core.exceptions import InvalidImage
from backend.core.logging import get_logger

logger = get_logger(__name__)


def remove_background(
    image: Image.Image,
    background: tuple[int, int, int] = (255, 255, 255),
) -> Image.Image:
    """Remove an image's background with ``rembg`` and flatten to RGB.

    The cut-out (RGBA) is composited onto a solid ``background`` colour so
    downstream models that expect 3-channel RGB (EfficientNet, OpenCLIP)
    receive a clean image instead of an alpha channel.

    ``rembg`` is imported lazily so this module imports fine where the
    (heavy) dependency is not installed.

    Args:
        image: Decoded RGB PIL image.
        background: Fill colour for the removed region.

    Returns:
        An RGB PIL image with the background replaced by ``background``.

    Raises:
        backend.core.exceptions.InvalidImage: If background removal fails.
    """
    try:
        from rembg import remove  # noqa: PLC0415
    except ImportError as exc:  # pragma: no cover - env-dependent
        raise InvalidImage(
            "rembg is not installed; cannot remove image background."
        ) from exc

    try:
        cutout = remove(image)  # RGBA PIL image
        if cutout.mode == "RGBA":
            flattened = Image.new("RGB", cutout.size, background)
            flattened.paste(cutout, mask=cutout.split()[3])
            return flattened
        return cutout.convert("RGB")
    except Exception as exc:  # noqa: BLE001
        raise InvalidImage(f"Background removal failed: {exc}") from exc


def load_image_from_bytes(content: bytes) -> Image.Image:
    """Decode raw bytes into a PIL image.

    Args:
        content: Raw image file bytes.

    Returns:
        A decoded PIL `Image` in RGB mode.

    Raises:
        backend.core.exceptions.InvalidImage: If `content` cannot be
            decoded as an image.
    """
    try:
        image = Image.open(io.BytesIO(content))
        image.load()
    except (UnidentifiedImageError, OSError) as exc:
        raise InvalidImage("Uploaded file is not a valid image.") from exc
    return image.convert("RGB")


def encode_thumbnail_data_url(
    image: Image.Image,
    max_side: int = 256,
    quality: int = 75,
) -> str:
    """Downscale an image and encode it as a base64 JPEG data URL.

    Uploads are never written to disk, so the prediction audit trail
    keeps its own copy inline. A data URL is self-contained — it needs no
    object storage behind it and drops straight into an `<img src>` — but
    it is stored per recorded prediction, which is why the defaults are
    deliberately small.

    Args:
        image: Decoded PIL image, in any mode.
        max_side: Longest edge of the result, in pixels.
        quality: JPEG quality (Pillow's 1-95 scale).

    Returns:
        A `data:image/jpeg;base64,...` URL of the downscaled image.
    """
    # JPEG carries neither alpha nor a palette, so anything but RGB has to
    # be flattened or `save` raises. `convert` also returns a new image,
    # which `thumbnail()` needs — it resizes in place and callers still
    # hold the original.
    downscaled = image.convert("RGB")
    downscaled.thumbnail((max_side, max_side))

    buffer = io.BytesIO()
    downscaled.save(buffer, format="JPEG", quality=quality)
    encoded = base64.b64encode(buffer.getvalue()).decode("ascii")
    return f"data:image/jpeg;base64,{encoded}"
