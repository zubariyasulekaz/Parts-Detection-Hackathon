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


async def close_db_engine() -> None:
    """Dispose of the engine's connection pool.

    Intended to be called once during application shutdown (see
    `backend.core.startup.on_shutdown`).
    """
    await engine.dispose()
    logger.info("Database engine connection pool disposed")
