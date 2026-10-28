"""
Stage 03 - Explainability.

Two complementary explanations per account:
  1. Rule contributions (additive by construction) -> "pass-through +28,
     structuring +18, ..." style plain-English narrative.
  2. SHAP on the account-level Isolation Forest -> which behavioral features
     drove the unsupervised anomaly component.

Outputs:
  output/explanations.csv            (ACID -> reason string + top rule drivers)
  output/shap_feature_importance.csv (global SHAP importance for the anomaly model)
"""
from __future__ import annotations
import argparse
import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import StandardScaler
import shap
from common import OUT, RULE_CAPS
import os

RANDOM_STATE = 42

RULE_LABELS = {
    "pass_through": "Pass-through (money in ~ money out)",
    "fan_in_aggregation": "Fan-in aggregation (collector account)",
    "structuring": "Structuring near Rs 50k CTR line",
    "new_account_burst": "New-account activity burst",
    "micro_credit_flood": "Micro-credit flood (UPI smurfing)",
    "high_lien_ratio": "High lien vs turnover",
}

# behavioral features fed to the account-level SHAP model
SHAP_FEATURES = [
    "passthrough_ratio", "credit_to_debit_ratio", "n_structuring",
    "txn_per_100d", "micro_credit_share", "lien_ratio",
    "amt_cv", "n_txn",
]


def reason_string(row: pd.Series) -> str:
    # each value is that rule's standalone risk (0-100); show the meaningful ones
    drivers = [(RULE_LABELS[r], row[r]) for r in RULE_CAPS if row[r] >= 10]
    drivers.sort(key=lambda x: -x[1])
    if not drivers:
        return "No strong rule triggers; flagged (if any) by anomaly model only."
    return "; ".join(f"{name} [standalone {pts:.0f}/100]" for name, pts in drivers)


def main() -> None:
    contrib = pd.read_csv(os.path.join(OUT, "rule_contributions.csv"))
    feat = pd.read_csv(os.path.join(OUT, "account_features.csv"))

    # ---- rule-based reason strings ----
    contrib["reason"] = contrib.apply(reason_string, axis=1)
    top_rule = contrib[["ACID", "reason"]].copy()

    # ---- SHAP on account-level Isolation Forest ----
    X = feat.set_index("ACID")[SHAP_FEATURES].fillna(0.0)
    Xs = StandardScaler().fit_transform(X)
    iso = IsolationForest(n_estimators=300, contamination="auto",
                          random_state=RANDOM_STATE).fit(Xs)

    # model output = -score_samples so higher = more anomalous
    f = lambda data: -iso.score_samples(data)
    explainer = shap.Explainer(f, Xs, feature_names=SHAP_FEATURES)
    sv = explainer(Xs)

    global_imp = (
        pd.DataFrame({"feature": SHAP_FEATURES,
                      "mean_abs_shap": np.abs(sv.values).mean(axis=0)})
        .sort_values("mean_abs_shap", ascending=False)
    )

    # per-account top SHAP driver
    acids = X.index.tolist()
    top_shap = []
    for i, acid in enumerate(acids):
        j = int(np.argmax(np.abs(sv.values[i])))
        top_shap.append({"ACID": acid,
                         "top_anomaly_feature": SHAP_FEATURES[j],
                         "top_anomaly_shap": round(float(sv.values[i][j]), 3)})
    top_shap = pd.DataFrame(top_shap)

    expl = top_rule.merge(top_shap, on="ACID", how="left")
    expl_path = os.path.join(OUT, "explanations.csv")
    expl.to_csv(expl_path, index=False)

    imp_path = os.path.join(OUT, "shap_feature_importance.csv")
    global_imp.round(4).to_csv(imp_path, index=False)

    print("Global SHAP importance (anomaly model):")
    print(global_imp.round(4).to_string(index=False))
    print(f"\n[03] wrote {expl_path}")
    print(f"[03] wrote {imp_path}")


def synthetic_explain() -> None:
    """SHAP on the supervised XGBoost model (exact TreeExplainer). Produces global
    feature importance + each account's top supervised driver — the real learned
    explanation the labelled synthetic data makes possible."""
    import supervised
    from common import load

    f01 = _load_features_module()
    feat = f01.build_features(load("synthetic")).set_index("ACID")
    model, X, y, cols = supervised.fit_full(feat)

    explainer = shap.TreeExplainer(model)
    sv = explainer.shap_values(X)
    sv = np.asarray(sv)
    if sv.ndim == 3:            # some shap/xgboost combos return (n, feat, class)
        sv = sv[..., -1]

    global_imp = (pd.DataFrame({"feature": cols, "mean_abs_shap": np.abs(sv).mean(axis=0)})
                  .sort_values("mean_abs_shap", ascending=False))

    rows = []
    for i, acid in enumerate(feat.index):
        j = int(np.argmax(np.abs(sv[i])))
        rows.append({"ACID": acid, "is_mule": int(y[i]),
                     "top_supervised_feature": cols[j],
                     "top_supervised_shap": round(float(sv[i][j]), 4)})
    expl = pd.DataFrame(rows)

    expl_path = os.path.join(OUT, "explanations_synthetic.csv")
    imp_path = os.path.join(OUT, "shap_feature_importance_synthetic.csv")
    expl.to_csv(expl_path, index=False)
    global_imp.round(4).to_csv(imp_path, index=False)

    print("Global SHAP importance (XGBoost supervised model):")
    print(global_imp.round(4).head(12).to_string(index=False))
    print(f"\n[03] wrote {expl_path}")
    print(f"[03] wrote {imp_path}")


def _load_features_module():
    import importlib.util
    p = os.path.join(os.path.dirname(__file__), "01_features.py")
    spec = importlib.util.spec_from_file_location("f01", p)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--source", choices=["real", "synthetic"], default="real")
    args = ap.parse_args()
    if args.source == "synthetic":
        synthetic_explain()
    else:
        main()
