"""
Stage 02 - Hybrid scoring: Rule Engine (+) Isolation Forest -> 0-100 composite.

Design (locked):
  * The transparent rule engine ANCHORS the score (N=19 makes a pure-ML term
    unstable). Rules combine via NOISY-OR so one strong typology already lifts
    the score and extra typologies compound it, capped at 100.
  * The Isolation Forest adds unsupervised "discovery". We run it at TWO levels
    and average them, because they catch different things:
      - transaction level (2000 rows)  -> odd individual transactions;
      - account level (19 rows)         -> structurally odd accounts
        (e.g. the 130:1 credit:debit collector), which a txn-level model misses.
  * composite = 0.65*rule + 0.35*anomaly.

Outputs:
  output/account_scores.csv          (per-account composite + components)
  output/rule_contributions.csv      (per-account, per-rule standalone risk 0-100)
"""
from __future__ import annotations
import argparse
import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import StandardScaler
from common import load, OUT, RULE_CAPS, W_RULE, W_ANOM
import os

RANDOM_STATE = 42

# Three-way fusion weights used ONLY when ground-truth labels exist (synthetic).
# When labels are available the supervised term leads; rules + anomaly stay in the
# mix as the interpretable anchor. The real path keeps the 2-way W_RULE/W_ANOM.
W_RULE_S, W_ANOM_S, W_SUP_S = 0.35, 0.15, 0.50

# account-level features fed to the structural Isolation Forest
ACCT_ANOM_FEATURES = [
    "passthrough_ratio", "credit_to_debit_ratio", "n_structuring",
    "txn_per_100d", "micro_credit_share", "lien_ratio", "amt_cv", "n_txn",
]


# --------------------------------------------------------------------------- #
# Rule engine: each rule -> severity in 0..1 per account.                       #
# --------------------------------------------------------------------------- #
def rule_severities(feat: pd.DataFrame) -> pd.DataFrame:
    s = pd.DataFrame(index=feat.index)
    active = (feat["amt_in"] > 0) & (feat["n_txn"] >= 5)

    # Pass-through: out/in near 1 AND little retained AND real activity.
    s["pass_through"] = np.clip((feat["passthrough_ratio"] - 0.7) / 0.3, 0, 1) * active

    # Fan-in aggregation: many credits per debit (collector account)
    s["fan_in_aggregation"] = np.clip((feat["credit_to_debit_ratio"] - 3) / 20, 0, 1)

    # Structuring: txns in the 45k-50k band; 2+ is full severity
    s["structuring"] = np.clip(feat["n_structuring"] / 2.0, 0, 1)

    # New-account burst: young account with high activity per 100 days
    young = feat["account_age_days"] < 400
    s["new_account_burst"] = np.clip((feat["txn_per_100d"] - 20) / 200, 0, 1) * young

    # Micro-credit flood: high share of sub-Rs-100 credits AND high credit count
    s["micro_credit_flood"] = (np.clip(feat["micro_credit_share"], 0, 1)
                               * np.clip(feat["n_credit"] / 100.0, 0, 1))

    # High lien relative to turnover
    s["high_lien_ratio"] = np.clip(feat["lien_ratio"], 0, 1)
    return s


def rule_points(feat: pd.DataFrame) -> pd.DataFrame:
    """Noisy-OR rule score + per-rule standalone risk (0-100) for explanations."""
    sev = rule_severities(feat)
    contrib = pd.DataFrame(index=feat.index)
    one_minus = pd.Series(1.0, index=feat.index)
    for rule, cap in RULE_CAPS.items():
        p = sev[rule] * cap                     # probability this rule alone implies mule
        contrib[rule] = (p * 100).round(2)      # standalone risk 0-100 (for narrative)
        one_minus *= (1.0 - p)
    contrib["rule_score"] = (100.0 * (1.0 - one_minus)).round(2)
    return contrib


# --------------------------------------------------------------------------- #
# Isolation Forest at two levels, each rank-normalized to 0-100.               #
# --------------------------------------------------------------------------- #
def _rank_norm(s: pd.Series) -> pd.Series:
    if s.nunique() <= 1:
        return pd.Series(0.0, index=s.index)
    return (s.rank(method="average") - 1) / (len(s) - 1) * 100.0


def _tx_anomaly(df: pd.DataFrame, feat: pd.DataFrame) -> pd.Series:
    tx = df.copy()
    tx["is_credit"] = (tx["PART_TRAN_TYPE"] == "C").astype(int)
    tx["log_amt"] = np.log1p(tx["TRAN_AMT"].clip(lower=0))
    tx["near_50k"] = ((tx["TRAN_AMT"] >= 45000) & (tx["TRAN_AMT"] < 50000)).astype(int)
    tx["is_upi"] = (tx["channel"] == "UPI").astype(int)
    cols = ["log_amt", "is_credit", "near_50k", "is_upi", "balance"]
    X = StandardScaler().fit_transform(tx[cols].fillna(0.0))
    iso = IsolationForest(n_estimators=300, contamination="auto", random_state=RANDOM_STATE).fit(X)
    tx["anom"] = -iso.score_samples(X)

    def rollup(s):  # mean of an account's most-anomalous quartile
        k = max(1, int(np.ceil(len(s) * 0.25)))
        return s.sort_values(ascending=False).head(k).mean()

    per = tx.groupby("ACID")["anom"].apply(rollup).reindex(feat.index)
    return _rank_norm(per)


def _acct_anomaly(feat: pd.DataFrame) -> pd.Series:
    X = feat[ACCT_ANOM_FEATURES].fillna(0.0)
    Xs = StandardScaler().fit_transform(X)
    iso = IsolationForest(n_estimators=300, contamination="auto", random_state=RANDOM_STATE).fit(Xs)
    score = pd.Series(-iso.score_samples(Xs), index=feat.index)
    return _rank_norm(score)


def anomaly_scores(df: pd.DataFrame, feat: pd.DataFrame) -> pd.Series:
    tx = _tx_anomaly(df, feat)
    ac = _acct_anomaly(feat)
    return (0.5 * tx + 0.5 * ac).reindex(feat.index)


def _suffix(source: str) -> str:
    return "" if source == "real" else f"_{source}"


def main(source: str = "real") -> None:
    suffix = _suffix(source)
    df = load(source)
    feat = pd.read_csv(os.path.join(OUT, f"account_features{suffix}.csv")).set_index("ACID")

    contrib = rule_points(feat)
    anom = anomaly_scores(df, feat)

    out = pd.DataFrame(index=feat.index)
    out["rule_score"] = contrib["rule_score"]
    out["anomaly_score"] = anom.round(1)

    labeled = "is_mule" in feat.columns
    if labeled:
        # supervised XGBoost term (out-of-fold, so the deliverable isn't in-sample)
        import supervised
        out["supervised_score"] = (supervised.oof_proba(feat) * 100).round(1)
        out["composite_risk"] = (
            W_RULE_S * out["rule_score"]
            + W_ANOM_S * out["anomaly_score"]
            + W_SUP_S * out["supervised_score"]
        ).round(1)
        out["is_mule"] = feat["is_mule"]
    else:
        out["composite_risk"] = (W_RULE * out["rule_score"] + W_ANOM * out["anomaly_score"]).round(1)

    out = out.sort_values("composite_risk", ascending=False).reset_index()

    scores_path = os.path.join(OUT, f"account_scores{suffix}.csv")
    out.to_csv(scores_path, index=False)

    contrib_out = contrib[list(RULE_CAPS) + ["rule_score"]].reset_index()
    contrib_path = os.path.join(OUT, f"rule_contributions{suffix}.csv")
    contrib_out.to_csv(contrib_path, index=False)

    print(out.to_string(index=False))
    print(f"\n[02] wrote {scores_path}")
    print(f"[02] wrote {contrib_path}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--source", choices=["real", "synthetic", "both"], default="real")
    args = ap.parse_args()
    main(args.source)
