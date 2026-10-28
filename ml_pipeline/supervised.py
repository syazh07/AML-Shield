"""
Supervised model (XGBoost) shared across scoring / explain / validate.

Only usable on the LABELED synthetic dataset — the real 19-account file has no
`is_mule` column, so nothing here touches the real Tier-A path. Kept in one place
so the scoring, SHAP and metrics stages all use an identical model + feature set.

Metrics are computed out-of-fold (cross_val_predict) so the per-account
supervised score in the deliverable is not optimistically in-sample.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
from sklearn.model_selection import StratifiedKFold, cross_val_predict

RANDOM_STATE = 42
N_SPLITS = 5
# columns that are NOT model inputs (label / provenance / identifiers)
_EXCLUDE = {"is_mule"}


def feature_columns(feat: pd.DataFrame) -> list[str]:
    """Numeric behavioural columns fed to the model (base + temporal + graph)."""
    num = feat.select_dtypes(include="number")
    return [c for c in num.columns if c not in _EXCLUDE]


def matrix(feat: pd.DataFrame):
    cols = feature_columns(feat)
    X = feat[cols].fillna(0.0).to_numpy()
    y = feat["is_mule"].astype(int).to_numpy()
    return X, y, cols


def build_model(y: np.ndarray | None = None):
    """XGBoost classifier with modest depth (guards against overfitting the
    known generative process) and class-imbalance weighting."""
    from xgboost import XGBClassifier

    spw = 1.0
    if y is not None:
        pos = int(np.sum(y == 1))
        neg = int(np.sum(y == 0))
        spw = (neg / pos) if pos else 1.0
    return XGBClassifier(
        n_estimators=300, max_depth=4, learning_rate=0.05,
        subsample=0.9, colsample_bytree=0.9, min_child_weight=2,
        eval_metric="logloss", random_state=RANDOM_STATE,
        scale_pos_weight=spw, n_jobs=0,
    )


def _cv(y: np.ndarray) -> StratifiedKFold:
    return StratifiedKFold(n_splits=N_SPLITS, shuffle=True, random_state=RANDOM_STATE)


def oof_proba(feat: pd.DataFrame) -> pd.Series:
    """Out-of-fold mule probability (0-1) for every labelled account."""
    X, y, _ = matrix(feat)
    proba = cross_val_predict(build_model(y), X, y, cv=_cv(y),
                              method="predict_proba")[:, 1]
    return pd.Series(proba, index=feat.index)


def fit_full(feat: pd.DataFrame):
    """Fit on all labelled data (for SHAP / feature importance). Returns
    (model, X, y, feature_names)."""
    X, y, cols = matrix(feat)
    model = build_model(y).fit(X, y)
    return model, X, y, cols
