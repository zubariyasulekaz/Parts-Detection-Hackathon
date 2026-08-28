"""FastAPI application factory.

Keeps `main.py` a thin entrypoint by centralizing app construction here:
router registration, middleware, exception handlers, and lifespan wiring.
"""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from backend.api.router import api_router
from backend.config.settings import get_settings
from backend.core.exceptions import (
    AuditEntryNotFound,
    CatalogError,
    CategoryNotFound,
    ChatSessionNotFound,
    ChatStateError,
    EmbeddingError,
    InvalidImage,
    ModelNotLoaded,
    PartPilotError,
    PredictionError,
    ProductAlreadyExists,
    ProductNotFound,
    SearchError,
)
from backend.core.logging import get_logger
from backend.core.startup import check_database, on_shutdown, on_startup
from backend.schemas.response import ErrorResponse

logger = get_logger(__name__)

# Maps domain exceptions to HTTP status codes for the exception handler below.
_EXCEPTION_STATUS_MAP: dict[type[PartPilotError], int] = {
    InvalidImage: status.HTTP_400_BAD_REQUEST,
    CategoryNotFound: status.HTTP_404_NOT_FOUND,
    CatalogError: status.HTTP_404_NOT_FOUND,
    ProductNotFound: status.HTTP_404_NOT_FOUND,
    AuditEntryNotFound: status.HTTP_404_NOT_FOUND,
    ChatSessionNotFound: status.HTTP_404_NOT_FOUND,
    ChatStateError: status.HTTP_400_BAD_REQUEST,
    ProductAlreadyExists: status.HTTP_409_CONFLICT,
    ModelNotLoaded: status.HTTP_503_SERVICE_UNAVAILABLE,
    EmbeddingError: status.HTTP_502_BAD_GATEWAY,
    SearchError: status.HTTP_502_BAD_GATEWAY,
    PredictionError: status.HTTP_500_INTERNAL_SERVER_ERROR,
}


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """FastAPI lifespan handler: runs startup routines, then shutdown on exit."""
    on_startup()
    await check_database()
    yield
    await on_shutdown()


def _register_exception_handlers(app: FastAPI) -> None:
    """Register handlers translating `PartPilotError` subclasses to `ErrorResponse`."""

    @app.exception_handler(PartPilotError)
    async def handle_partpilot_error(request: Request, exc: PartPilotError) -> JSONResponse:
        status_code = _EXCEPTION_STATUS_MAP.get(type(exc), status.HTTP_500_INTERNAL_SERVER_ERROR)
        logger.error("%s: %s", exc.error_code, exc.message)
        body = ErrorResponse(error_code=exc.error_code, message=exc.message)
        return JSONResponse(status_code=status_code, content=body.model_dump())


def create_app() -> FastAPI:
    """Application factory.

    Returns:
        A fully configured `FastAPI` instance, ready to be served by
        Uvicorn (see `main.py`).
    """
    settings = get_settings()

    app = FastAPI(
        title=settings.APP_NAME,
        version=settings.APP_VERSION,
        debug=settings.DEBUG,
        lifespan=lifespan,
    )

    # A wildcard origin and credentials are mutually exclusive under CORS: a
    # browser rejects `Access-Control-Allow-Origin: *` when the response also
    # allows credentials, and the request fails as a network error with no
    # useful message. The preflight still succeeds, because Starlette echoes
    # the real origin there and only falls back to "*" on the actual response -
    # so the API answers fine from curl and only breaks in the browser.
    #
    # Nothing here uses cookies or auth headers, so drop credentials rather
    # than the wildcard, which would otherwise have to list every port Vite
    # might pick.
    allow_credentials = "*" not in settings.CORS_ORIGINS

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=allow_credentials,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    _register_exception_handlers(app)

    app.include_router(api_router, prefix=settings.API_PREFIX)

    # RigidHitch product photographs, served from disk when a directory is
    # configured. Only for demos and local development - in production the
    # client's own CDN serves them and RIGIDHITCH_IMAGE_BASE_URL points there
    # instead, with this left unset.
    #
    # Without some URL the images are invisible rather than broken: the
    # frontend keeps only http(s) URLs and silently substitutes a placeholder
    # for anything else, so relative paths produce a page of grey boxes with
    # nothing in the logs to explain it.
    if settings.RIGIDHITCH_IMAGE_DIR:
        image_dir = Path(settings.RIGIDHITCH_IMAGE_DIR)
        if image_dir.is_dir():
            app.mount(
                "/rigidhitch-images",
                StaticFiles(directory=str(image_dir)),
                name="rigidhitch-images",
            )
            logger.info("Serving RigidHitch images from %s", image_dir)
        else:
            logger.warning(
                "RIGIDHITCH_IMAGE_DIR is set to %s but that directory does not "
                "exist - RigidHitch product images will not load.", image_dir
            )

    return app


_app = create_app()
_settings = get_settings()

# Wrap the complete application so CORS headers are also present on unhandled
# errors returned by Starlette's outer ServerErrorMiddleware.
app = CORSMiddleware(
    _app,
    allow_origins=_settings.CORS_ORIGINS,
    allow_credentials="*" not in _settings.CORS_ORIGINS,
    allow_methods=["*"],
    allow_headers=["*"],
)
