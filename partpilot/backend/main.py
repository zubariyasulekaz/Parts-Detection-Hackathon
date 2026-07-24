"""Uvicorn entrypoint.

Run with:
    python -m backend.main
or directly via Uvicorn's CLI:
    uvicorn backend.app:app --reload
"""

import uvicorn

from backend.config.settings import get_settings


def run() -> None:
    """Start the Uvicorn server using host/port from application settings."""
    settings = get_settings()
    uvicorn.run(
        "backend.app:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG,
        log_level=settings.LOG_LEVEL.lower(),
    )


if __name__ == "__main__":
    run()
