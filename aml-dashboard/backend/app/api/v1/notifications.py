from __future__ import annotations

from fastapi import APIRouter, Depends, Request

from app.core.state import AppState
from app.models.schemas import NotificationItem

router = APIRouter(prefix="/notifications", tags=["notifications"])


def get_state(request: Request) -> AppState:
    return request.app.state.container


@router.get("", response_model=list[NotificationItem])
def list_notifications(state: AppState = Depends(get_state)) -> list[NotificationItem]:
    return state.notifications.list()


@router.patch("/read-all")
def mark_all_read(state: AppState = Depends(get_state)) -> dict:
    return {"updated": state.notifications.mark_all_read()}


@router.patch("/{notification_id}/read")
def mark_read(notification_id: int, state: AppState = Depends(get_state)) -> dict:
    return {"id": notification_id, "read": state.notifications.mark_read(notification_id)}


@router.delete("/{notification_id}")
def dismiss(notification_id: int, state: AppState = Depends(get_state)) -> dict:
    return {"id": notification_id, "dismissed": state.notifications.dismiss(notification_id)}
