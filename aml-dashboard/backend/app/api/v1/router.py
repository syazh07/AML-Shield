from __future__ import annotations

from fastapi import APIRouter

from app.api.v1 import admin, cases, copilot, health, ml, notifications, session, str

api_router = APIRouter()
api_router.include_router(health.router)
api_router.include_router(session.router)
api_router.include_router(cases.router)
api_router.include_router(str.router)
api_router.include_router(ml.router)
api_router.include_router(notifications.router)
api_router.include_router(admin.router)
api_router.include_router(copilot.router)
