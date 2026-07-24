"""Health check endpoint.

Used by load balancers / orchestration platforms (Kubernetes liveness
and readiness probes) to determine whether the service is up.
"""

from fastapi import APIRouter

from backend.config.settings import Settings, get_settings
from backend.schemas.response import StandardResponse

router = APIRouter(prefix="/health", tags=["Health"])


@router.get("", response_model=StandardResponse[dict])
async def health_check() -> StandardResponse[dict]:
    """Return basic service liveness/version information.

    TODO: Extend readiness checks once real model/index loading exists
    (e.g. report whether Brain 1-3 resources are loaded).
    """
    settings: Settings = get_settings()
    return StandardResponse(
        data={
            "status": "ok",
            "app_name": settings.APP_NAME,
            "version": settings.APP_VERSION,
            "environment": settings.ENV,
        }
    )
