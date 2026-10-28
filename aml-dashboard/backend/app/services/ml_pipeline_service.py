"""Real ML scoring, plugged in from the project's own `ml_pipeline/` model.

This replaces the 2-rule placeholder. At startup it loads `ml_pipeline/common.py`
(reusing its exact IOB rule caps and data loader) and fits the same
transaction-level Isolation Forest on the real sample data. Live transactions are
then scored through that model + noisy-OR rules — the same hybrid the offline
pipeline uses. Demonstrates the thesis literally: the model is a swappable plug
behind the `/ml/score` interface, and `is_placeholder` is now False.
"""
from __future__ import annotations

import importlib.util
import os

import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import StandardScaler

from app.models.schemas import CaseScoreResult, SignalContribution, TransactionFeatures

_HERE = os.path.dirname(os.path.abspath(__file__))
_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(_HERE))))
_ML_COMMON = os.path.join(_REPO_ROOT, "ml_pipeline", "common.py")


def _load_ml_common():
    spec = importlib.util.spec_from_file_location("ml_pipeline_common", _ML_COMMON)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _clip(v: float) -> float:
    return max(0.0, min(1.0, v))


def _rup(n: float) -> str:
    return "₹" + f"{n:,.0f}"


# rich risk-signal card metadata per account typology
_RULE_META = {
    "pass_through": ("Pass-Through Pattern", "RULE_PASS_THROUGH", "Σ(outflow) ÷ inflow ≥ 0.85"),
    "fan_in_aggregation": ("Fan-Out Structure", "RULE_FANOUT", "distinct_recipients(window) ≥ 3"),
    "structuring": ("Structuring / Smurfing", "RULE_STRUCTURING", "txn amount in ₹45k–₹50k band"),
}


class MLPipelineScoringService:
    """The ml_pipeline hybrid plugged in behind the connector.

    Structurally implements `app.services.scoring.ScoringModel` — the only surface
    the rest of the backend depends on. Swap this class for any other conforming
    model without touching endpoints, schemas, or the workstation.
    """

    MODEL_VERSION = "ml_pipeline-hybrid-v1"
    MODEL_TYPE = "rules_noisyOR+isolation_forest"
    IS_PLACEHOLDER = False

    def __init__(self) -> None:
        ml = _load_ml_common()
        self._caps = ml.RULE_CAPS
        self._w_rule = ml.W_RULE
        self._w_anom = ml.W_ANOM

        df = ml.load_raw()  # the project's own sample transactions
        tx = self._tx_features(df["TRAN_AMT"], df["PART_TRAN_TYPE"] == "C",
                               df["channel"] == "UPI", df["balance"].fillna(0.0))
        self._scaler = StandardScaler().fit(tx)
        self._iso = IsolationForest(n_estimators=300, contamination="auto",
                                    random_state=42).fit(self._scaler.transform(tx))
        train = -self._iso.score_samples(self._scaler.transform(tx))
        self._lo, self._hi = float(train.min()), float(train.max())

    @staticmethod
    def _tx_features(amount, is_credit, is_upi, balance) -> np.ndarray:
        amount = np.asarray(amount, dtype=float)
        near_50k = ((amount >= 45000) & (amount < 50000)).astype(float)
        return np.column_stack([
            np.log1p(np.clip(amount, 0, None)),
            np.asarray(is_credit, dtype=float),
            near_50k,
            np.asarray(is_upi, dtype=float),
            np.asarray(balance, dtype=float),
        ])

    def _anomaly_0_100(self, vec: np.ndarray) -> float:
        raw = -self._iso.score_samples(self._scaler.transform(vec))[0]
        if self._hi <= self._lo:
            return 0.0
        return float(np.clip((raw - self._lo) / (self._hi - self._lo), 0, 1) * 100)

    async def score_transaction(self, features: TransactionFeatures) -> CaseScoreResult:
        amount = features.amount
        is_credit = features.direction == "credit"
        is_upi = features.channel.upper() == "UPI"
        balance = float(features.metadata.get("balance", 0.0))
        near_50k = 45000 <= amount < 50000
        is_micro = amount < 100 and is_credit

        vec = self._tx_features([amount], [is_credit], [is_upi], [balance])
        anomaly = self._anomaly_0_100(vec)

        # noisy-OR over the transaction-applicable IOB typologies (real rule caps)
        signals: list[SignalContribution] = []
        one_minus = 1.0
        if near_50k:
            p = self._caps["structuring"]
            one_minus *= (1 - p)
            signals.append(SignalContribution(rule="RULE_STRUCTURING", points=int(p * 100),
                weight=round(p, 2), description=f"Amount ₹{amount:,.0f} just under the ₹50k CTR line"))
        if is_micro:
            p = self._caps["micro_credit_flood"]
            one_minus *= (1 - p)
            signals.append(SignalContribution(rule="RULE_MICRO_CREDIT", points=int(p * 100),
                weight=round(p, 2), description=f"Micro-credit ₹{amount:,.0f} (UPI smurfing signature)"))
        rule_score = 100.0 * (1 - one_minus)

        signals.append(SignalContribution(rule="ISOLATION_FOREST_ANOMALY", points=int(anomaly),
            weight=round(self._w_anom, 2),
            description=f"Unsupervised anomaly {anomaly:.0f}/100 vs learned transaction baseline"))

        composite = int(round(self._w_rule * rule_score + self._w_anom * anomaly))
        return CaseScoreResult(
            case_id=features.account_id,
            score=min(100, composite),
            model_version=self.MODEL_VERSION,
            model_type=self.MODEL_TYPE,
            signals=signals,
            explanation=(
                f"Scored by the plugged-in ml_pipeline hybrid model: rules "
                f"{rule_score:.0f}/100 ⊕ Isolation Forest anomaly {anomaly:.0f}/100 "
                f"(weights {self._w_rule:.2f}/{self._w_anom:.2f})."
            ),
            is_placeholder=False,
        )

    def score_account(self, bundle: dict) -> dict:
        """Score a case's actual behaviour (its investigation timeline/graph) through
        the ml_pipeline hybrid: noisy-OR account rules ⊕ Isolation Forest. Returns a
        composite 0-100 score AND rich risk-signal cards, so the pool score, the
        investigation total, and the signal breakdown all trace to one real model.
        """
        tl = bundle.get("timeline", [])
        credits = [t for t in tl if t["dir"] == "credit"]
        debits = [t for t in tl if t["dir"] == "debit"]
        inflow = sum(t["amt"] for t in credits)
        outflow = sum(t["amt"] for t in debits)
        ratio = (outflow / inflow) if inflow else 0.0
        recipients = {t["party"] for t in debits}
        n_struct = sum(1 for t in tl if 45000 <= t["amt"] < 50000)
        primary_id = next((n["id"] for n in bundle["graph"]["nodes"] if n.get("role") == "primary"), None)
        hl = {"type": "node", "id": primary_id}

        severities = {
            "pass_through": _clip((ratio - 0.7) / 0.3),
            "fan_in_aggregation": _clip((len(recipients) - 2) / 5.0),
            "structuring": _clip(n_struct / 2.0),
        }
        evidence_by_rule = {
            "pass_through": [
                {"k": "Inflow", "v": _rup(inflow)},
                {"k": "Forwarded", "v": _rup(outflow)},
                {"k": "Ratio", "v": f"{ratio * 100:.0f}% (threshold 85%)", "emp": True},
            ],
            "fan_in_aggregation": [
                {"k": "Distinct recipients", "v": str(len(recipients)), "emp": True},
                {"k": "Debit legs", "v": str(len(debits))},
            ],
            "structuring": [
                {"k": "Txns in ₹45k–₹50k band", "v": str(n_struct), "emp": True},
            ],
        }

        # Isolation Forest anomaly on the largest inflow (a big credit to a mule is odd)
        main = max(credits, key=lambda t: t["amt"]) if credits else None
        if main:
            vec = self._tx_features([main["amt"]], [True], [main.get("channel", "").upper() == "UPI"], [0.0])
            anomaly = self._anomaly_0_100(vec)
        else:
            anomaly = 0.0

        cards: list[dict] = []
        one_minus = 1.0
        for rule, sev in severities.items():
            p = sev * self._caps[rule]
            if p <= 0.05:
                continue
            one_minus *= (1 - p)
            title, rule_code, formula = _RULE_META[rule]
            cards.append({
                "id": rule, "title": title, "pts": max(1, round(p * 30)),
                "desc": f"{title} detected in this account's flow", "highlight": hl,
                "rule": rule_code, "formula": formula, "evidence": evidence_by_rule[rule],
                "model": {"weight": f"{self._caps[rule]:.2f}", "precision": "—", "trained": "2,000 txns (sample)"},
                "trace": f"{self.MODEL_VERSION} · noisy-OR rule",
            })
        rule_score = 100.0 * (1 - one_minus)

        cards.append({
            "id": "anomaly", "title": "Isolation Forest Anomaly", "pts": max(1, round(anomaly / 100 * 30)),
            "desc": f"Unsupervised anomaly {anomaly:.0f}/100 vs learned transaction baseline",
            "highlight": hl, "rule": "ISOLATION_FOREST_ANOMALY",
            "formula": "−score_samples(x) normalised over the sample distribution",
            "evidence": [
                {"k": "Anomaly score", "v": f"{anomaly:.0f}/100", "emp": True},
                {"k": "Largest inflow", "v": _rup(main["amt"]) if main else "—"},
            ],
            "model": {"weight": f"{self._w_anom:.2f}", "precision": "—", "trained": "2,000 txns (sample)"},
            "trace": f"{self.MODEL_VERSION} · isolation_forest",
        })

        composite = int(round(min(100, self._w_rule * rule_score + self._w_anom * anomaly)))
        return {"score": composite, "signals": cards, "anomaly": anomaly, "rule_score": rule_score}
