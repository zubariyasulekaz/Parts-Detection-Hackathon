"""FastAPI application factory.

Keeps `main.py` a thin entrypoint by centralizing app construction here:
router registration, middleware, exception handlers, and lifespan wiring.
"""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from backend.api.router import api_router
from backend.config.settings import get_settings
from backend.core.exceptions import (
    AuditEntryNotFound,
    CatalogError,
    CategoryNotFound,
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
from backend.core.startup import on_shutdown, on_startup
from backend.schemas.response import ErrorResponse

logger = get_logger(__name__)

# Maps domain exceptions to HTTP status codes for the exception handler below.
_EXCEPTION_STATUS_MAP: dict[type[PartPilotError], int] = {
    InvalidImage: status.HTTP_400_BAD_REQUEST,
    CategoryNotFound: status.HTTP_404_NOT_FOUND,
    CatalogError: status.HTTP_404_NOT_FOUND,
    ProductNotFound: status.HTTP_404_NOT_FOUND,
    AuditEntryNotFound: status.HTTP_404_NOT_FOUND,
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

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    _register_exception_handlers(app)

    app.include_router(api_router, prefix=settings.API_PREFIX)

    return app


app = create_app()
