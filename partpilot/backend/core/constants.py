"""Application-wide constants.

Anything that is a fixed, non-configurable value belongs here. Values
that a deployment might want to override belong in `backend.config.settings`
instead.
"""

from typing import Final

# --- API ---------------------------------------------------------------
API_V1_PREFIX: Final[str] = "/api/v1"

# --- Brain 1: classifier ---------------------------------------------------------------
# The trained classifier label set (matches labels.json produced during training,
# in the model's output order).
PLACEHOLDER_CATEGORY_LABELS: Final[list[str]] = [
    "air_filter",
    "brake_pads",
    "exhaust_manifold",
    "fuel_injector",
    "oil_filter",
    "power_steering_pump",
    "shock_absorber",
    "suspension_bushing",
    "throttle_body",
    "wheel_hub_assembly",
]

# Maps a classifier label (or its slug) to the catalog category string used
# in catalog.csv / FAISS index filenames. Needed because the classifier's
# label set (e.g. "brake_pads") can differ from the catalog category
# ("Brake Pads"). Keyed by slug (lowercase, non-alnum -> "_").
CATEGORY_ALIASES: Final[dict[str, str]] = {
    "air_filter": "Air Filter",
    "brake_pad": "Brake Pads",
    "brake_pads": "Brake Pads",
    "exhaust_manifold": "Exhaust Manifold",
    "fuel_injector": "Fuel Injector",
    "oil_filter": "Oil Filter",
    "power_steering_pump": "Power Steering Pump",
    "shock_absorber": "Shock Absorber",
    "suspension_bushing": "Suspension Bushing",
    "throttle_body": "Throttle Body",
    "wheel_hub_assembly": "Wheel Hub Assembly",
}

# --- images ---------------------------------------------------------------
SUPPORTED_IMAGE_MIME_TYPES: Final[list[str]] = [
    "image/jpeg",
    "image/png",
    "image/webp",
]

# --- misc ---------------------------------------------------------------
DEFAULT_REQUEST_ID_HEADER: Final[str] = "X-Request-ID"
