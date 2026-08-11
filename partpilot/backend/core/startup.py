"""Application startup and shutdown lifecycle hooks.

Wired into the FastAPI app via a `lifespan` context manager in
`backend.app`. Keeping this logic here (instead of inline in `app.py`)
makes it independently testable and keeps `app.py` focused on wiring.
"""

from time import perf_counter

from sqlalchemy import text

from backend.config.paths import ensure_runtime_directories
from backend.config.settings import get_settings
from backend.core.database import close_db_engine, engine
from backend.core.logging import configure_logging, get_logger

logger = get_logger(__name__)


def on_startup() -> None:
    """Run all startup routines.

    Brain 3 (product catalog) needs no warm-up beyond the connectivity
    check below: it is backed by PostgreSQL via a request-scoped
    `AsyncSession` (see `backend.core.database.get_db`), not an
    in-memory cache.
    """
    configure_logging()
    ensure_runtime_directories()
    logger.info("PartPilot backend starting up")
    if get_settings().WARM_MODELS_ON_STARTUP:
        warm_models()


async def check_database() -> None:
    """Fail loudly at boot, not silently on the judge's first upload.

    A DB outage otherwise surfaces only when a user submits a photo -
    Brain 1/2 run for several seconds first, then the request dies on
    catalog lookup. Checking here puts the failure (and the fix) in the
    startup log where whoever is running the demo will actually see it
    before an audience does.

    `db.<project>.supabase.co` (Supabase's direct connection) resolves
    over IPv6 only; a network without IPv6 routing fails with a
    low-level connect error that gives no hint what to do. The session
    pooler (`aws-0-<region>.pooler.supabase.com`) is IPv4-reachable and
    is what `docs/RUNNING.md` recommends for exactly this reason.
    """
    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
    except Exception as exc:  # noqa: BLE001
        hint = (
            " This looks like the IPv6-only Supabase direct-connection host - "
            "switch DATABASE_URL to the session pooler "
            "(aws-0-<region>.pooler.supabase.com:5432, username "
            "postgres.<project-ref>). See docs/RUNNING.md."
            if "10060" in str(exc) or "10061" in str(exc) or "Connect call failed" in str(exc)
            else " Check DATABASE_URL in .env - see docs/RUNNING.md for troubleshooting."
        )
        logger.error(
            "Cannot reach the database - Brain 3 catalog lookups will fail on every "
            "upload until this is fixed: %s.%s",
            exc,
            hint,
        )
    else:
        logger.info("Database reachable")


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

    Brain 4 is warmed only when `WARM_BRAIN4_ON_STARTUP` is set. It used to
    be left cold unconditionally because the `transformers` path loads
    several GB; the quantised GGUF the llama.cpp path reads is a fraction of
    that and loads in seconds, which is worth paying at boot rather than
    making whoever uploads first wait it out.
    """
    from PIL import Image  # noqa: PLC0415

    from backend.api.dependencies import (  # noqa: PLC0415
        get_classifier,
        get_reasoning_service,
        get_similarity_search,
    )
    from backend.utils.image_utils import remove_background  # noqa: PLC0415

    dummy = Image.new("RGB", (224, 224), (128, 128, 128))

    steps = [
        ("rembg", lambda: remove_background(dummy)),
        ("Brain 1 classifier", lambda: get_classifier().predict(dummy)),
        ("Brain 2 indexes + embedding models", lambda: _warm_similarity(get_similarity_search())),
    ]
    if get_settings().WARM_BRAIN4_ON_STARTUP:
        steps.append(("Brain 4 reasoning model", lambda: _warm_reasoning(get_reasoning_service())))
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


def _warm_reasoning(service: object) -> None:
    """Warm a reasoning service if it supports warming.

    Same optional contract as `_warm_similarity`: `ReasoningInterface` only
    requires `explain`, so a backend with nothing to preload (or a test
    double) is simply skipped.
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
