from __future__ import annotations

from datetime import datetime

from app.models.schemas import (
    CaseDetail,
    CaseScoreResult,
    CaseStatus,
    CaseSummary,
    SignalContribution,
    TransactionFeatures,
)
from app.persistence import Store
from app.services.audit_service import AuditService
from app.services.notification_service import NotificationService
from app.services.scoring import ScoringModel
from app.data import seed
from app.data.investigation_gen import generate_bundle


class GenericMLScoringService:
    """Placeholder ML service — replace with real model inference later."""

    MODEL_VERSION = "generic-stub-v0.1.0"
    MODEL_TYPE = "rule_weighted_stub"

    async def score_transaction(self, features: TransactionFeatures) -> CaseScoreResult:
        base = 35
        if features.amount >= 100_000:
            base += 25
        if features.direction == "credit" and features.amount >= 400_000:
            base += 20
        signals = [
            SignalContribution(
                rule="GENERIC_AMOUNT_THRESHOLD",
                points=min(40, int(features.amount / 25_000)),
                weight=0.35,
                description=f"Amount {features.amount:,.0f} via {features.channel}",
            )
        ]
        score = min(100, base)
        return CaseScoreResult(
            case_id=features.account_id,
            score=score,
            model_version=self.MODEL_VERSION,
            model_type=self.MODEL_TYPE,
            signals=signals,
            explanation="Generic stub scorer — swap GenericMLScoringService for production model.",
            is_placeholder=True,
        )

    async def score_case(self, case_id: str) -> CaseScoreResult:
        case = next((c for c in seed.CASES if c["id"] == case_id), None)
        if not case:
            raise KeyError(case_id)

        signals = [
            SignalContribution(
                rule=s["rule"],
                points=s["pts"],
                weight=float(s["model"]["weight"]),
                description=s["desc"],
            )
            for s in seed.RISK_SIGNALS
        ]
        return CaseScoreResult(
            case_id=case_id,
            score=case["score"],
            flag=case["flag"],
            model_version=self.MODEL_VERSION,
            model_type=self.MODEL_TYPE,
            signals=signals,
            explanation="Score derived from seeded risk signals until ML pipeline is connected.",
            is_placeholder=True,
        )


class CaseService:
    def __init__(
        self,
        store: Store,
        audit: AuditService,
        ml: ScoringModel,
        notifications: NotificationService,
    ) -> None:
        self._store = store
        self._audit = audit
        self._ml = ml
        self._notifications = notifications
        # load cache from the persistent store (seeded by build_app_state)
        self._cases: dict[str, dict] = {}
        self._str_status: dict[str, str] = {}
        self._confidence: dict[str, int] = {}
        for wrapper in store.all_cases():
            case = wrapper["case"]
            self._cases[case["id"]] = case
            if wrapper.get("confidence") is not None:
                self._confidence[case["id"]] = wrapper["confidence"]
            self._str_status[case["id"]] = wrapper.get("strStatus", "none")
        self._notes: dict[str, list[dict]] = store.notes_by_case()

    def _persist(self, case_id: str) -> None:
        self._store.save_case(
            self._cases[case_id],
            self._confidence.get(case_id),
            self._str_status.get(case_id, "none"),
        )

    def list_cases(
        self,
        *,
        flag: str | None = None,
        status: str | None = None,
        score_min: int = 0,
        score_max: int = 100,
        search: str | None = None,
    ) -> list[CaseSummary]:
        rows = list(self._cases.values())
        if flag and flag != "all":
            rows = [r for r in rows if r["flag"] == flag]
        if status and status != "all":
            rows = [r for r in rows if r["status"] == status]
        rows = [r for r in rows if score_min <= r["score"] <= score_max]
        if search:
            q = search.lower()
            rows = [r for r in rows if q in r["id"].lower() or q in r["account"].lower()]
        return [CaseSummary(**row) for row in rows]

    def get_case(self, case_id: str) -> CaseDetail:
        row = self._cases.get(case_id)
        if not row:
            raise KeyError(case_id)
        return CaseDetail(**row, str_status=self._str_status.get(case_id, "none"))

    @staticmethod
    def _actor(name: str) -> str:
        parts = name.split()
        return f"{parts[0][:1]}.{parts[-1]}" if len(parts) > 1 else name

    def add_case(self, case: dict) -> CaseDetail:
        """Ingest a new case. Its behaviour (timeline/graph) is scored by the real
        ml_pipeline model, and that score + signal breakdown drive the case."""
        case_id = case["id"]
        if case_id in self._cases:
            raise ValueError("Case already exists")
        case = dict(case)
        bundle = generate_bundle(case)
        result = self._ml.score_account(bundle)
        case["score"] = result["score"]
        bundle["total_score"] = result["score"]
        bundle["risk_signals"] = result["signals"]
        self._cases[case_id] = case
        self._str_status[case_id] = "none"
        self._persist(case_id)
        self._store.save_investigation(case_id, bundle)
        self._audit.append(case_id, "TM-ENGINE",
                           f"Alert scored {result['score']}/100 by {self._ml.MODEL_VERSION}")
        self._notifications.emit_new_case(case)
        return self.get_case(case_id)

    def get_investigation(self, case_id: str) -> dict:
        if case_id not in self._cases:
            raise KeyError(case_id)
        bundle = self._store.get_investigation(case_id)
        if bundle is None:  # safety net for any case created before bundles existed
            bundle = generate_bundle(self._cases[case_id])
            self._store.save_investigation(case_id, bundle)
        return bundle

    def claim(self, case_id: str, analyst_name: str) -> CaseDetail:
        row = self._cases[case_id]
        if row["status"] != "unclaimed":
            raise ValueError("Case is not unclaimed")
        row["status"] = "in-progress"
        row["claimedBy"] = analyst_name
        self._persist(case_id)
        self._audit.append(case_id, self._actor(analyst_name), "Case claimed")
        self._audit.append(case_id, "AML-SYS", "Status → IN_PROGRESS")
        return self.get_case(case_id)

    def close(self, case_id: str, reason: str, actor: str = "Priya Venkatesh") -> CaseDetail:
        row = self._cases[case_id]
        row["status"] = "closed"
        row["closedReason"] = reason
        row["strDeadlineHrs"] = None
        self._persist(case_id)
        self._audit.append(case_id, self._actor(actor), f"Case closed · {reason}")
        self._notifications.emit_case_closed(case_id, actor, reason)
        return self.get_case(case_id)

    def handoff(self, case_id: str, recipient_handle: str, note: str, actor: str = "Priya Venkatesh") -> CaseDetail:
        row = self._cases[case_id]
        row["claimedBy"] = recipient_handle
        self._persist(case_id)
        self._audit.append(case_id, self._actor(actor), f"Handoff → {recipient_handle}: {note}")
        return self.get_case(case_id)

    def escalate(self, case_id: str, officer_id: str, note: str, priority: str, actor: str = "Priya Venkatesh") -> CaseDetail:
        row = self._cases[case_id]
        row["status"] = "review"
        self._persist(case_id)
        self._audit.append(case_id, self._actor(actor), f"Escalated to {officer_id} ({priority}): {note}")
        self._notifications.emit_escalation(case_id, actor, officer_id, priority)
        return self.get_case(case_id)

    def update_confidence(self, case_id: str, confidence: int) -> int:
        self._confidence[case_id] = confidence
        self._persist(case_id)
        self._audit.append(case_id, "P.Venkatesh", f"Confidence updated → {confidence}%")
        return confidence

    def get_confidence(self, case_id: str) -> int:
        return self._confidence.get(case_id, 50)

    def list_notes(self, case_id: str) -> list[dict]:
        return self._notes.get(case_id, [])

    def add_note(self, case_id: str, body: str, mentions: list[str]) -> dict:
        note_id = max((n["id"] for n in self._notes.get(case_id, [])), default=0) + 1
        note = {
            "id": note_id,
            "kind": "user",
            "author": seed.CURRENT_USER["name"],
            "role": seed.CURRENT_USER["role"],
            "time": datetime.now().strftime("%H:%M:%S"),
            "body": body,
            "mentions": mentions,
        }
        self._notes.setdefault(case_id, []).append(note)
        self._store.save_note(case_id, note)
        self._audit.append(case_id, "P.Venkatesh", f"Note added (audit-{note_id})")
        return note

    def set_str_status(self, case_id: str, status: str) -> None:
        self._str_status[case_id] = status
        if case_id in self._cases:
            self._persist(case_id)

    def get_str_status(self, case_id: str) -> str:
        return self._str_status.get(case_id, "none")

    async def rescore_case(self, case_id: str) -> CaseScoreResult:
        row = self._cases.get(case_id)
        if not row:
            raise KeyError(case_id)
        result = self._ml.score_account(self.get_investigation(case_id))
        signals = [
            SignalContribution(rule=s["rule"], points=s["pts"],
                               weight=float(s["model"]["weight"]), description=s["desc"])
            for s in result["signals"]
        ]
        return CaseScoreResult(
            case_id=case_id, score=result["score"], flag=row["flag"],
            model_version=self._ml.MODEL_VERSION, model_type=self._ml.MODEL_TYPE,
            signals=signals,
            explanation="Scored by the ml_pipeline hybrid on this case's transaction pattern.",
            is_placeholder=False,
        )
