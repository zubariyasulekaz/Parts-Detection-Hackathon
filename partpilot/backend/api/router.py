"""Top-level API router aggregating all sub-routers.

Mounted onto the FastAPI app (under `Settings.API_PREFIX`) in
`backend.app.create_app`.
"""

from fastapi import APIRouter

from backend.api.routers import admin, catalog, health, prediction

api_router = APIRouter()

api_router.include_router(health.router)
api_router.include_router(prediction.router)
api_router.include_router(catalog.router)
api_router.include_router(admin.router)
