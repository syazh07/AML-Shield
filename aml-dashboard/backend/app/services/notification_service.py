from __future__ import annotations

from app.models.schemas import NotificationItem
from app.persistence import Store


class NotificationService:
    """Notification feed with real read/dismiss state, persisted to SQLite.

    Loaded from the store on startup; the case pipeline and the demo seeder push
    new items via `add`, which is what makes the dashboard feel live when polled.
    """

    def __init__(self, store: Store) -> None:
        self._store = store
        self._items: list[NotificationItem] = [
            NotificationItem(**n) for n in store.all_notifications()
        ]
        self._next_id = max((n.id for n in self._items), default=0) + 1

    def list(self) -> list[NotificationItem]:
        # newest first
        return list(reversed(self._items))

    def add(
        self,
        *,
        type: str,
        color: str,
        icon: str,
        title: str,
        msg: str,
        action: str,
        case_id: str | None = None,
        time: str = "just now",
    ) -> NotificationItem:
        item = NotificationItem(
            id=self._next_id,
            type=type,
            color=color,
            icon=icon,
            title=title,
            time=time,
            msg=msg,
            action=action,
            caseId=case_id,
            read=False,
        )
        self._items.append(item)
        self._next_id += 1
        self._store.save_notification(item.model_dump(by_alias=True))
        return item

    def mark_read(self, notification_id: int) -> bool:
        for item in self._items:
            if item.id == notification_id:
                item.read = True
                self._store.save_notification(item.model_dump(by_alias=True))
                return True
        return False

    def mark_all_read(self) -> int:
        count = 0
        for item in self._items:
            if not item.read:
                item.read = True
                self._store.save_notification(item.model_dump(by_alias=True))
                count += 1
        return count

    def dismiss(self, notification_id: int) -> bool:
        before = len(self._items)
        self._items = [i for i in self._items if i.id != notification_id]
        if len(self._items) != before:
            self._store.delete_notification(notification_id)
            return True
        return False

    # --- convenience emitters used by the case pipeline / seeder ------------- #
    def emit_new_case(self, case: dict) -> NotificationItem:
        critical = case["score"] >= 85
        return self.add(
            type="deadline" if critical else "info",
            color="#ef4444" if critical else "#0ea5e9",
            icon="!" if critical else "＋",
            title="New Critical Case" if critical else "New Case",
            msg=(
                f'New {"critical " if critical else ""}case auto-generated: '
                f'<span class="case-ref">{case["id"]}</span>. '
                f'Risk Score {case["score"]}. Flag: {case["flag"]}. Unclaimed.'
            ),
            action="Claim",
            case_id=case["id"],
        )

    def emit_case_closed(self, case_id: str, actor: str, reason: str) -> NotificationItem:
        return self.add(
            type="info",
            color="#64748b",
            icon="✓",
            title="Case Update",
            msg=f'{actor} closed case <span class="case-ref">{case_id}</span> as {reason}.',
            action="View",
            case_id=case_id,
        )

    def emit_escalation(self, case_id: str, actor: str, officer: str, priority: str) -> NotificationItem:
        return self.add(
            type="escalation",
            color="#f59e0b",
            icon="↑",
            title="Escalation Received",
            msg=(
                f'Case <span class="case-ref">{case_id}</span> escalated to {officer} '
                f'by {actor} for senior review. Priority: {priority.capitalize()}.'
            ),
            action="Review",
            case_id=case_id,
        )
