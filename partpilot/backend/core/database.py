"""Async SQLAlchemy engine and session management for the RigidHitch catalogue.

Single source of truth for the async engine, session factory, and the
`get_rigidhitch_db` dependency that request-scoped catalogue reads are built on
(see `backend.api.dependencies`).

The engine is built lazily, on first use, rather than at import time. An engine
constructed at import runs before logging is configured and before the app can
report anything useful, and it makes importing this module - which the tests and
the offline scripts do - depend on a database being configured.
"""

from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from backend.config.settings import get_settings
from backend.core.logging import get_logger

logger = get_logger(__name__)

_engine: AsyncEngine | None = None
_session_factory: async_sessionmaker[AsyncSession] | None = None


def get_rigidhitch_session_factory() -> async_sessionmaker[AsyncSession]:
    """Session factory for the RigidHitch catalogue, created on first use.

    Raises:
        RuntimeError: If ``RIGIDHITCH_DATABASE_URL`` is unset. Failing here is
            better than returning an engine pointed at nothing and letting the
            first product lookup fail with a driver-level error.
    """
    global _engine, _session_factory
    if _session_factory is not None:
        return _session_factory

    settings = get_settings()
    url = settings.RIGIDHITCH_DATABASE_URL
    if not url:
        raise RuntimeError(
            "RIGIDHITCH_DATABASE_URL is not set, so the RigidHitch catalogue "
            "cannot be served. Add it to .env - see docs/RIGIDHITCH.md."
        )

    _engine = create_async_engine(
        url,
        echo=settings.DB_ECHO,
        pool_size=settings.DB_POOL_SIZE,
        max_overflow=settings.DB_MAX_OVERFLOW,
        pool_pre_ping=True,
    )
    _session_factory = async_sessionmaker(
        bind=_engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autoflush=False,
    )
    logger.info("RigidHitch database engine created")
    return _session_factory


async def get_rigidhitch_db() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency yielding a request-scoped session on the RigidHitch DB.

    Commits when the handler returns without raising; rolls back on any
    exception. The session is always closed at the end of the request.
    """
    async with get_rigidhitch_session_factory()() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def close_rigidhitch_engine() -> None:
    """Dispose the engine at shutdown, if one was ever created."""
    global _engine, _session_factory
    if _engine is not None:
        await _engine.dispose()
        _engine = None
        _session_factory = None
        logger.info("RigidHitch database engine disposed")
