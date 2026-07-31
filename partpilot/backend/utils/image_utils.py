"""Generic image I/O helpers.

Only basic decode/encode plumbing lives here. Model-specific
pre-processing (resizing, normalization, background removal) belongs in
`backend.pipeline.brain1_classifier.preprocess` / the Brain 2 embedding
pipeline instead, since that logic is model-dependent.
"""

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
