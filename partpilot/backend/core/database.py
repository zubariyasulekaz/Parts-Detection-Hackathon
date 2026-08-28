"""Async SQLAlchemy database engine and session management.

Single source of truth for the async engine, session factory, and
declarative `Base` that ORM models (e.g. `backend.pipeline.brain3_catalog.models.Product`)
inherit from. `get_db` is the FastAPI dependency request-scoped
repositories are built on top of (see `backend.api.dependencies`).
"""

import socket
from collections.abc import AsyncGenerator
from urllib.parse import urlsplit

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase

from backend.config.settings import Settings, get_settings
from backend.core.logging import get_logger

logger = get_logger(__name__)


class Base(DeclarativeBase):
    """Declarative base class shared by all SQLAlchemy ORM models."""


def _has_ipv6_route(host: str, port: int, timeout: float) -> bool:
    """Best-effort check for a live IPv6 route to `host:port`.

    Checking AF_INET6 socket support alone is not enough: a machine can
    support IPv6 sockets while the *network* has no IPv6 route to a given
    host, and DNS resolution for an IPv6-only host (Supabase's direct
    connection endpoint) succeeds independently of whether that route
    exists. The only reliable signal is an actual, short-timeout TCP
    connect attempt.
    """
    try:
        candidates = socket.getaddrinfo(host, port, socket.AF_INET6, socket.SOCK_STREAM)
    except socket.gaierror:
        return False

    for family, socktype, proto, _, sockaddr in candidates:
        try:
            with socket.socket(family, socktype, proto) as probe:
                probe.settimeout(timeout)
                probe.connect(sockaddr)
                return True
        except OSError:
            continue
    return False


def _resolve_database_url(settings: Settings) -> str:
    """Pick `DATABASE_URL`, or fall back to `DATABASE_URL_POOLER`.

    Supabase's direct connection host is IPv6-only (see
    partpilot/docs/RUNNING.md); a network without IPv6 routing doesn't fail
    that connection fast, it hangs until the driver's own timeout. Resolving
    the choice once, synchronously, at engine-build time turns that into an
    immediate, logged fallback instead of a confusing per-request stall.
    """
    if not settings.DATABASE_URL_POOLER:
        return settings.DATABASE_URL

    parsed = urlsplit(settings.DATABASE_URL)
    host, port = parsed.hostname, parsed.port or 5432

    if host and _has_ipv6_route(host, port, settings.DB_IPV6_CHECK_TIMEOUT_SECONDS):
        return settings.DATABASE_URL

    logger.warning(
        "No IPv6 route to %s:%s - using DATABASE_URL_POOLER instead",
        host,
        port,
    )
    return settings.DATABASE_URL_POOLER


def _build_engine() -> AsyncEngine:
    settings = get_settings()
    return create_async_engine(
        _resolve_database_url(settings),
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


# --- RigidHitch -------------------------------------------------------------
# A second client catalogue, in its own database with a different products
# schema. Kept as a separate engine rather than a schema inside the first: the
# two have different columns, different lifecycles, and belong to different
# clients, so a mistake in one must not be able to reach the other.
#
# Built lazily. Most deployments serve only PartPilot, and an engine for a
# database that was never configured should cost nothing and fail only when
# something actually asks for it.
_rigidhitch_engine: AsyncEngine | None = None
_rigidhitch_session_factory: async_sessionmaker[AsyncSession] | None = None


def get_rigidhitch_session_factory() -> async_sessionmaker[AsyncSession]:
    """Session factory for the RigidHitch catalogue, created on first use.

    Raises:
        RuntimeError: If ``RIGIDHITCH_DATABASE_URL`` is unset — better than
            silently falling back to PartPilot's database and serving one
            client's catalogue under another's name.
    """
    global _rigidhitch_engine, _rigidhitch_session_factory
    if _rigidhitch_session_factory is not None:
        return _rigidhitch_session_factory

    settings = get_settings()
    url = settings.RIGIDHITCH_DATABASE_URL
    if not url:
        raise RuntimeError(
            "RIGIDHITCH_DATABASE_URL is not set, so the RigidHitch catalogue "
            "cannot be served. Add it to .env - see docs/RIGIDHITCH.md."
        )

    _rigidhitch_engine = create_async_engine(
        url,
        echo=settings.DB_ECHO,
        pool_size=settings.DB_POOL_SIZE,
        max_overflow=settings.DB_MAX_OVERFLOW,
        pool_pre_ping=True,
    )
    _rigidhitch_session_factory = async_sessionmaker(
        bind=_rigidhitch_engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autoflush=False,
    )
    logger.info("RigidHitch database engine created")
    return _rigidhitch_session_factory


async def get_rigidhitch_db() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency yielding a request-scoped session on the RigidHitch DB."""
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
    """Dispose the RigidHitch engine at shutdown, if one was ever created."""
    global _rigidhitch_engine, _rigidhitch_session_factory
    if _rigidhitch_engine is not None:
        await _rigidhitch_engine.dispose()
        _rigidhitch_engine = None
        _rigidhitch_session_factory = None


async def close_db_engine() -> None:
    """Dispose of the engine's connection pool.

    Intended to be called once during application shutdown (see
    `backend.core.startup.on_shutdown`).
    """
    await engine.dispose()
    logger.info("Database engine connection pool disposed")
