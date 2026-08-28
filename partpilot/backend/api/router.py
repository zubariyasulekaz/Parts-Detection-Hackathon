"""Top-level API router aggregating all sub-routers.

Mounted onto the FastAPI app (under `Settings.API_PREFIX`) in
`backend.app.create_app`.
"""

from fastapi import APIRouter

from backend.api.routers import admin, catalog, chat, health, history, prediction, rigidhitch

api_router = APIRouter()

api_router.include_router(health.router)
api_router.include_router(prediction.router)
api_router.include_router(chat.router)
api_router.include_router(history.router)
api_router.include_router(catalog.router)
api_router.include_router(admin.router)
# Second client catalogue, on its own routes and its own database. Its
# endpoints fail with a clear message when RIGIDHITCH_DATABASE_URL is unset,
# so a PartPilot-only deployment is unaffected by their presence.
api_router.include_router(rigidhitch.router)
