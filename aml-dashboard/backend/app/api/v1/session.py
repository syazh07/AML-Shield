from __future__ import annotations

from fastapi import APIRouter

from app.data import seed

router = APIRouter(prefix="/session", tags=["session"])


@router.get("")
def get_session() -> dict:
    """The logged-in investigator + team roster (the frontend renders these
    instead of hardcoding an identity)."""
    return {"user": seed.CURRENT_USER, "team": seed.TEAM}
