"""Top-level API router aggregating all sub-routers.

Mounted onto the FastAPI app (under `Settings.API_PREFIX`) in
`backend.app.create_app`.
"""

from fastapi import APIRouter

from backend.api.routers import health, rigidhitch

api_router = APIRouter()

api_router.include_router(health.router)
api_router.include_router(rigidhitch.router)
