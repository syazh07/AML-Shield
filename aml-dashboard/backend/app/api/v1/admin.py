from __future__ import annotations

from fastapi import APIRouter, Request

from app.core.state import build_app_state

router = APIRouter(prefix="/admin", tags=["admin"])


@router.post("/reset")
def reset_demo(request: Request) -> dict:
    """Wipe the SQLite store, re-seed the base demo state, and swap in a fresh
    service graph — returns the dashboard to its clean base without a restart.
    Used between demo runs (see backend/reset_db.py)."""
    request.app.state.container = build_app_state(reset=True)
    cases = request.app.state.container.cases.list_cases()
    return {"status": "reset", "cases": len(cases)}
