"""Generic image I/O helpers.

Only basic decode/encode plumbing lives here. Model-specific
pre-processing (resizing, normalization, background removal) belongs in
`backend.pipeline.brain1_classifier.preprocess` / the Brain 2 embedding
pipeline instead, since that logic is model-dependent.
"""

import io

from PIL import Image, UnidentifiedImageError

from backend.core.exceptions import InvalidImage


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
