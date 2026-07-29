"""Async SQLAlchemy database engine and session management.

Single source of truth for the async engine, session factory, and
declarative `Base` that ORM models (e.g. `backend.pipeline.brain3_catalog.models.Product`)
inherit from. `get_db` is the FastAPI dependency request-scoped
repositories are built on top of (see `backend.api.dependencies`).
"""

from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase

from backend.config.settings import get_settings
from backend.core.logging import get_logger

logger = get_logger(__name__)


class Base(DeclarativeBase):
    """Declarative base class shared by all SQLAlchemy ORM models."""


def _build_engine() -> AsyncEngine:
    settings = get_settings()
    return create_async_engine(
        settings.DATABASE_URL,
        echo=settings.DB_ECHO,
        pool_size=settings.DB_POOL_SIZE,
        max_overflow=settings.DB_MAX_OVERFLOW,
        pool_pre_ping=True,
    )


# Engine creation is lazy w.r.t. actual DB connections (asyncpg only
# connects on first use), so constructing this at import time is safe
# even when no database is reachable yet (e.g. during test collection).
engine: AsyncEngine = _build_engine()

async_session_factory: async_sessionmaker[AsyncSession] = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency yielding a request-scoped `AsyncSession`.

    Commits automatically when the request handler returns without
    raising; rolls back on any exception. The session is always closed
    at the end of the request.
    """
    async with async_session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def close_db_engine() -> None:
    """Dispose of the engine's connection pool.

    Intended to be called once during application shutdown (see
    `backend.core.startup.on_shutdown`).
    """
    await engine.dispose()
    logger.info("Database engine connection pool disposed")
