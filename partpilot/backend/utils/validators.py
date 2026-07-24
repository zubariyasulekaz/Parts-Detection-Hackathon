"""Generic input validation helpers (file extension/size, etc.).

Pure infrastructure (no AI logic), so implemented directly rather than
left as a stub.
"""

from pathlib import Path

from backend.config.settings import get_settings
from backend.core.exceptions import InvalidImage


def validate_image_extension(filename: str) -> None:
    """Validate that `filename` has an allowed image extension.

    Raises:
        backend.core.exceptions.InvalidImage: If the extension is not in
            `Settings.ALLOWED_IMAGE_EXTENSIONS`.
    """
    settings = get_settings()
    extension = Path(filename).suffix.lower()
    if extension not in settings.ALLOWED_IMAGE_EXTENSIONS:
        raise InvalidImage(
            f"Unsupported file extension '{extension}'. "
            f"Allowed: {settings.ALLOWED_IMAGE_EXTENSIONS}"
        )


def validate_image_size(size_bytes: int) -> None:
    """Validate that an uploaded image does not exceed the configured max size.

    Raises:
        backend.core.exceptions.InvalidImage: If `size_bytes` exceeds
            `Settings.MAX_UPLOAD_SIZE_MB`.
    """
    settings = get_settings()
    max_bytes = settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024
    if size_bytes > max_bytes:
        raise InvalidImage(
            f"Image size {size_bytes} bytes exceeds the "
            f"{settings.MAX_UPLOAD_SIZE_MB}MB limit."
        )
