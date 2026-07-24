"""Application-wide constants.

Anything that is a fixed, non-configurable value belongs here. Values
that a deployment might want to override belong in `backend.config.settings`
instead.
"""

from typing import Final

# --- API ---------------------------------------------------------------
API_V1_PREFIX: Final[str] = "/api/v1"

# --- Brain 1: classifier ---------------------------------------------------------------
# TODO: Replace with the final trained label set for the classifier.
PLACEHOLDER_CATEGORY_LABELS: Final[list[str]] = [
    "oil_filter",
    "brake_pad",
    "air_filter",
    "spark_plug",
    "cabin_filter",
]

# --- images ---------------------------------------------------------------
SUPPORTED_IMAGE_MIME_TYPES: Final[list[str]] = [
    "image/jpeg",
    "image/png",
    "image/webp",
]

# --- misc ---------------------------------------------------------------
DEFAULT_REQUEST_ID_HEADER: Final[str] = "X-Request-ID"
