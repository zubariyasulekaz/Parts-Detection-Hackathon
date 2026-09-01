"""Application startup and shutdown lifecycle hooks.

Wired into the FastAPI app via a `lifespan` context manager in `backend.app`.
Keeping this logic here (instead of inline in `app.py`) makes it independently
testable and keeps `app.py` focused on wiring.
"""

from time import perf_counter

from sqlalchemy import text

from backend.config.paths import ensure_runtime_directories
from backend.config.settings import get_settings
from backend.core.database import close_rigidhitch_engine, get_rigidhitch_session_factory
from backend.core.logging import configure_logging, get_logger

logger = get_logger(__name__)


def on_startup() -> None:
    """Run all startup routines.

    The catalogue needs no warm-up beyond the connectivity check below: it is
    read from PostgreSQL through a request-scoped `AsyncSession`, not held in
    memory.
    """
    configure_logging()
    ensure_runtime_directories()
    logger.info("RigidHitch part finder starting up")
    if get_settings().WARM_MODELS_ON_STARTUP:
        warm_models()


async def check_database() -> None:
    """Fail loudly at boot, not silently on the client's first upload.

    A database outage otherwise surfaces only once someone submits a photo -
    the search runs for a couple of seconds first, then the request dies on the
    catalogue lookup. Checking here puts the failure, and the fix, in the
    startup log where whoever is running the demo will see it before an
    audience does.
    """
    try:
        factory = get_rigidhitch_session_factory()
        async with factory() as session:
            await session.execute(text("SELECT 1"))
    except Exception as exc:  # noqa: BLE001
        logger.error(
            "Cannot reach the RigidHitch database - every search will return "
            "matches with no product details until this is fixed: %s. Check "
            "RIGIDHITCH_DATABASE_URL in .env.",
            exc,
        )
    else:
        logger.info("RigidHitch database reachable")


def warm_models() -> None:
    """Load the model and index before the first request.

    Without this the first upload pays rembg and a 330 MB fine-tuned vision
    transformer loading inside the request - twenty seconds or more on a cold
    process, with a spinner and no explanation. On a laptop this went unnoticed
    because a script had usually loaded the model already; on a server it lands
    on whoever opens the link first.

    Warming goes through `backend.api.dependencies` so it heats the very
    singleton requests will use - warming a private copy would heat nothing.

    Every step is best-effort: a model that cannot load logs a warning here and
    fails exactly as it would have inside the request, just earlier and without
    someone waiting on it.
    """
    from PIL import Image  # noqa: PLC0415

    from backend.api.dependencies import get_app_settings, get_rigidhitch_search  # noqa: PLC0415
    from backend.utils.image_utils import remove_background  # noqa: PLC0415

    dummy = Image.new("RGB", (224, 224), (128, 128, 128))

    def warm_search() -> None:
        # A real search rather than `warm()`: the generic warm-up walks the
        # index directory's own categories, and RigidHitch's index is a single
        # sentinel category in a directory of its own, so it would be skipped.
        # One search loads the index, the whitening transform and the model,
        # which is exactly what the first request needs.
        get_rigidhitch_search().search(
            category=get_app_settings().RIGIDHITCH_CATEGORY,
            image=dummy,
            top_k=1,
            raw_image=dummy,
        )

    steps = [
        ("rembg", lambda: remove_background(dummy)),
        ("RigidHitch index + embedding model", warm_search),
    ]
    for name, step in steps:
        started = perf_counter()
        try:
            step()
        except Exception as exc:  # noqa: BLE001
            logger.warning("Warm-up for %s failed (first request will retry): %s", name, exc)
        else:
            logger.info("Warmed %s in %.1fs", name, perf_counter() - started)


async def on_shutdown() -> None:
    """Run all shutdown routines."""
    await close_rigidhitch_engine()
    logger.info("RigidHitch part finder shutting down")
