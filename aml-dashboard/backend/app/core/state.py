from __future__ import annotations

from dataclasses import dataclass

from app.data.seeding import seed_base
from app.persistence import Store
from app.services.audit_service import AuditService
from app.services.case_service import CaseService
from app.services.copilot_service import CopilotService
from app.services.ml_pipeline_service import MLPipelineScoringService
from app.services.notification_service import NotificationService
from app.services.scoring import ScoringModel
from app.services.str_service import STRGenerationService


@dataclass
class AppState:
    store: Store
    audit: AuditService
    # the model-agnostic connector seam — any ScoringModel implementation plugs in
    ml: ScoringModel
    notifications: NotificationService
    cases: CaseService
    str_service: STRGenerationService
    copilot: CopilotService


def build_app_state(*, reset: bool = False) -> AppState:
    """Construct the service graph over a SQLite-backed store.

    On first run (empty DB) the base demo state is seeded. Passing reset=True
    wipes the DB and re-seeds base — this is how the demo returns to a clean
    slate between runs, without restarting the process.
    """
    store = Store()
    if reset:
        store.wipe()
    ml = MLPipelineScoringService()
    if store.is_empty():
        seed_base(store, ml)

    audit = AuditService(store)
    notifications = NotificationService(store)
    cases = CaseService(store, audit, ml, notifications)
    str_service = STRGenerationService(cases, audit, store)
    copilot = CopilotService(cases)

    return AppState(
        store=store,
        audit=audit,
        ml=ml,
        notifications=notifications,
        cases=cases,
        str_service=str_service,
        copilot=copilot,
    )
