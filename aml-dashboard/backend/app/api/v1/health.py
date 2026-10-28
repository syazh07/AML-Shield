from __future__ import annotations

from fastapi import APIRouter, Depends, Request

from app.config import settings
from app.core.state import AppState
from app.data import seed
from app.models.schemas import HealthResponse

router = APIRouter(tags=["health"])


def get_state(request: Request) -> AppState:
    return request.app.state.container


@router.get("/health", response_model=HealthResponse)
def health(state: AppState = Depends(get_state)) -> HealthResponse:
    return HealthResponse(
        status="ok",
        app=settings.app_name,
        openai_configured=bool(settings.openai_api_key),
        ml_model=state.ml.MODEL_VERSION,
    )


@router.get("/me")
def current_user() -> dict:
    return seed.CURRENT_USER


@router.get("/team")
def team() -> list[dict]:
    return seed.TEAM
