"""Generic filesystem helpers (directory management, saving uploads).

Pure infrastructure (no AI logic), so implemented directly rather than
left as a stub.
"""

import uuid
from pathlib import Path


def ensure_directory(path: Path) -> Path:
    """Create `path` (and parents) if it does not already exist.

    Returns:
        The same `path`, for convenient chaining.
    """
    path.mkdir(parents=True, exist_ok=True)
    return path


def generate_unique_filename(original_filename: str) -> str:
    """Generate a collision-resistant filename that preserves the extension.

    Args:
        original_filename: The client-supplied filename.

    Returns:
        A `"<uuid4><original-extension>"` string.
    """
    extension = Path(original_filename).suffix.lower()
    return f"{uuid.uuid4().hex}{extension}"


def save_upload_bytes(content: bytes, destination: Path) -> Path:
    """Write raw upload bytes to `destination`, creating parent dirs as needed.

    Returns:
        The path the file was written to.
    """
    ensure_directory(destination.parent)
    destination.write_bytes(content)
    return destination
