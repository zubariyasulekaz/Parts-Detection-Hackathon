"""Security-related dependencies (API key auth, etc.).

Placeholder implementation only. The current behavior is intentionally
permissive (no-op) when `Settings.API_KEY` is unset, so the skeleton runs
out of the box. Tighten this before shipping to production.
"""

from fastapi import Header, HTTPException, status

from backend.config.settings import get_settings
from backend.core.logging import get_logger

logger = get_logger(__name__)


async def verify_api_key(x_api_key: str | None = Header(default=None)) -> None:
    """FastAPI dependency that validates the `X-API-Key` header.

    TODO: Replace with a real auth scheme (OAuth2/JWT, API gateway, etc.)
    before this service is exposed outside a trusted network.

    Args:
        x_api_key: The value of the `X-API-Key` request header, if present.

    Raises:
        HTTPException: 401 if an `API_KEY` is configured and the header is
            missing or does not match.
    """
    settings = get_settings()

    if settings.API_KEY is None:
        # No API key configured -> auth disabled (development mode).
        return

    if x_api_key != settings.API_KEY:
        logger.warning("Rejected request with invalid or missing API key")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing API key",
        )
