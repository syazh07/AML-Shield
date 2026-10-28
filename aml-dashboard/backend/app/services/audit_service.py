from __future__ import annotations

import hashlib
import secrets
from datetime import datetime, timezone

from app.models.schemas import AuditEntry
from app.persistence import Store


class AuditService:
    def __init__(self, store: Store) -> None:
        self._store = store
        self._logs: dict[str, list[AuditEntry]] = {
            case_id: [AuditEntry(**e) for e in entries]
            for case_id, entries in store.audit_by_case().items()
        }

    def list_for_case(self, case_id: str) -> list[AuditEntry]:
        return list(self._logs.get(case_id, []))

    def append(self, case_id: str, actor: str, action: str) -> AuditEntry:
        now = datetime.now(timezone.utc)
        ts = now.strftime("%H:%M:%S")
        payload = f"{case_id}|{actor}|{action}|{now.isoformat()}|{secrets.token_hex(8)}"
        digest = hashlib.sha256(payload.encode()).hexdigest()[:8]
        entry = AuditEntry(ts=ts, actor=actor, action=action, hash=f"{digest[:4]}…{digest[4:8]}")
        self._logs.setdefault(case_id, []).append(entry)
        self._store.append_audit(case_id, entry.model_dump())
        return entry
