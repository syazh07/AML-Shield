"""
Stage 05 - Final report.

Fuses scores + explanations into the deliverable the investigator sees:
  output/flagged_mule_accounts.csv

Columns: ACID, Risk_Score, Is_Flagged, Top_Reasons, Anomaly_Score, Rule_Score,
         Top_Anomaly_Feature
"""
from __future__ import annotations
import argparse
import pandas as pd
from common import OUT, FLAG_THRESHOLD, short
import os


def main() -> None:
    scores = pd.read_csv(os.path.join(OUT, "account_scores.csv"))
    expl = pd.read_csv(os.path.join(OUT, "explanations.csv"))

    rep = scores.merge(expl, on="ACID", how="left")
    rep["Is_Flagged"] = rep["composite_risk"] >= FLAG_THRESHOLD
    rep["ACID_short"] = rep["ACID"].map(short)

    out = rep[[
        "ACID_short", "ACID", "composite_risk", "Is_Flagged", "reason",
        "rule_score", "anomaly_score", "top_anomaly_feature",
    ]].rename(columns={
        "ACID_short": "Account",
        "composite_risk": "Risk_Score",
        "reason": "Top_Reasons",
        "rule_score": "Rule_Score",
        "anomaly_score": "Anomaly_Score",
        "top_anomaly_feature": "Top_Anomaly_Feature",
    }).sort_values("Risk_Score", ascending=False)

    path = os.path.join(OUT, "flagged_mule_accounts.csv")
    out.round(1).to_csv(path, index=False)

    n_flag = int(out["Is_Flagged"].sum())
    print(out.round(1).to_string(index=False))
    print(f"\n[05] {n_flag}/{len(out)} accounts flagged at threshold {FLAG_THRESHOLD}")
    print(f"[05] wrote {path}")


def synthetic_report() -> None:
    """Deliverable for the synthetic scenario: composite risk + supervised driver
    + whether each flag was CORRECT against ground truth (only possible because
    the synthetic data is labelled)."""
    scores = pd.read_csv(os.path.join(OUT, "account_scores_synthetic.csv"))
    expl = pd.read_csv(os.path.join(OUT, "explanations_synthetic.csv"))
    rep = scores.merge(expl[["ACID", "top_supervised_feature", "top_supervised_shap"]],
                       on="ACID", how="left")
    rep["Is_Flagged"] = rep["composite_risk"] >= FLAG_THRESHOLD
    rep["Account"] = rep["ACID"].map(short)
    # correctness of the flag decision vs the ground-truth label
    rep["Correct"] = rep["Is_Flagged"] == rep["is_mule"].astype(bool)
    out = rep[[
        "Account", "ACID", "composite_risk", "Is_Flagged", "is_mule", "Correct",
        "rule_score", "anomaly_score", "supervised_score", "top_supervised_feature",
    ]].rename(columns={
        "composite_risk": "Risk_Score", "is_mule": "True_Mule",
        "rule_score": "Rule_Score", "anomaly_score": "Anomaly_Score",
        "supervised_score": "Supervised_Score", "top_supervised_feature": "Top_Supervised_Feature",
    }).sort_values("Risk_Score", ascending=False)

    path = os.path.join(OUT, "flagged_mule_accounts_synthetic.csv")
    out.round(1).to_csv(path, index=False)

    n_flag = int(out["Is_Flagged"].sum())
    acc = out["Correct"].mean() * 100
    print(out.head(15).round(1).to_string(index=False))
    print(f"\n[05] {n_flag}/{len(out)} accounts flagged; flag accuracy vs ground truth: {acc:.1f}%")
    print(f"[05] wrote {path}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--source", choices=["real", "synthetic"], default="real")
    args = ap.parse_args()
    if args.source == "synthetic":
        synthetic_report()
    else:
        main()
