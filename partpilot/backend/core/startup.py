"""Application startup and shutdown lifecycle hooks.

Wired into the FastAPI app via a `lifespan` context manager in
`backend.app`. Keeping this logic here (instead of inline in `app.py`)
makes it independently testable and keeps `app.py` focused on wiring.
"""

from backend.config.paths import ensure_runtime_directories
from backend.core.database import close_db_engine
from backend.core.logging import configure_logging, get_logger

logger = get_logger(__name__)


def on_startup() -> None:
    """Run all startup routines.

    TODO: Once Brain 1, 2 and 4 have real implementations, initialize/warm
    the following here (or via a dedicated resource container injected
    through `backend.api.dependencies`):
        - Load the Brain 1 classifier weights.
        - Load the OpenCLIP model for Brain 2.
        - Load/attach the per-category FAISS indexes.

    Brain 3 (product catalog) needs no warm-up: it is backed by
    PostgreSQL via a request-scoped `AsyncSession` (see
    `backend.core.database.get_db`), not an in-memory cache.
    """
    configure_logging()
    ensure_runtime_directories()
    logger.info("PartPilot backend starting up")


async def on_shutdown() -> None:
    """Run all shutdown routines.

    TODO: Release model/GPU resources, close FAISS index handles, flush
    any buffered metrics, etc.
    """
    await close_db_engine()
    logger.info("PartPilot backend shutting down")
