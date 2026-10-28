"""The model-agnostic scoring seam.

The backend is a *connector*: it never trains or hard-codes a detector, it only
depends on this narrow interface. Any model — the current ml_pipeline hybrid
(rules ⊕ Isolation Forest), a future supervised XGBoost trained on labelled data,
or an external scoring service — is a drop-in as long as it satisfies
`ScoringModel`. Nothing else in the app (`state.py`, `api/v1/ml.py`,
`api/v1/health.py`, `data/seeding.py`, `services/case_service.py`) reaches past
these members.

This is a structural (duck-typed) Protocol: implementers do NOT need to subclass
it. `MLPipelineScoringService` already conforms.
"""
from __future__ import annotations

from typing import Protocol, runtime_checkable

from app.models.schemas import CaseScoreResult, TransactionFeatures


@runtime_checkable
class ScoringModel(Protocol):
    """The full contract the backend relies on for risk scoring."""

    # --- identity (surfaced by /ml/info and /health) -------------------------
    MODEL_VERSION: str
    MODEL_TYPE: str
    IS_PLACEHOLDER: bool

    async def score_transaction(self, features: TransactionFeatures) -> CaseScoreResult:
        """Score a single transaction's features → composite risk + signal cards."""
        ...

    def score_account(self, bundle: dict) -> dict:
        """Score a case's account behaviour (its investigation bundle) → dict with
        `score` (0-100), `signals` (risk-signal cards), `anomaly`, `rule_score`."""
        ...
