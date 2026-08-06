"""Application startup and shutdown lifecycle hooks.

Wired into the FastAPI app via a `lifespan` context manager in
`backend.app`. Keeping this logic here (instead of inline in `app.py`)
makes it independently testable and keeps `app.py` focused on wiring.
"""

from time import perf_counter

from backend.config.paths import ensure_runtime_directories
from backend.config.settings import get_settings
from backend.core.database import close_db_engine
from backend.core.logging import configure_logging, get_logger

logger = get_logger(__name__)


def on_startup() -> None:
    """Run all startup routines.

    Brain 3 (product catalog) needs no warm-up: it is backed by
    PostgreSQL via a request-scoped `AsyncSession` (see
    `backend.core.database.get_db`), not an in-memory cache.
    """
    configure_logging()
    ensure_runtime_directories()
    logger.info("PartPilot backend starting up")
    if get_settings().WARM_MODELS_ON_STARTUP:
        warm_models()


def warm_models() -> None:
    """Load Brain 1/2 weights and indexes before the first request.

    Without this, the first upload pays rembg + TensorFlow + a vision
    transformer all loading inside the request — a 30-60s stall on a cold
    process. Every step is best-effort: a model that cannot load logs a
    warning here and fails (or degrades) exactly as it would have inside
    the request, just earlier and without a user waiting on it.

    Warming goes through `backend.api.dependencies` so it touches the very
    singletons requests will use — warming private copies would heat
    nothing.

    Brain 4 is deliberately left cold: it is optional, degrades to
    "no explanation", and its weights are the largest of the lot.
    """
    from PIL import Image  # noqa: PLC0415

    from backend.api.dependencies import get_classifier, get_similarity_search  # noqa: PLC0415
    from backend.utils.image_utils import remove_background  # noqa: PLC0415

    dummy = Image.new("RGB", (224, 224), (128, 128, 128))

    steps = [
        ("rembg", lambda: remove_background(dummy)),
        ("Brain 1 classifier", lambda: get_classifier().predict(dummy)),
        ("Brain 2 indexes + embedding models", lambda: _warm_similarity(get_similarity_search())),
    ]
    for name, step in steps:
        started = perf_counter()
        try:
            step()
        except Exception as exc:  # noqa: BLE001
            logger.warning("Warm-up for %s failed (first request will retry): %s", name, exc)
        else:
            logger.info("Warmed %s in %.1fs", name, perf_counter() - started)


def _warm_similarity(service: object) -> None:
    """Warm a similarity-search service if it supports warming.

    The interface deliberately does not require `warm()` — a remote or
    test implementation has nothing to load.
    """
    warm = getattr(service, "warm", None)
    if callable(warm):
        warm()


async def on_shutdown() -> None:
    """Run all shutdown routines.

    TODO: Release model/GPU resources, close FAISS index handles, flush
    any buffered metrics, etc.
    """
    await close_db_engine()
    logger.info("PartPilot backend shutting down")
