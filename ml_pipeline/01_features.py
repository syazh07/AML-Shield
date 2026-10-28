"""
Stage 01 - Account-level feature engineering.

Aggregates the 2000 transactions into one row per account (ACID) using ONLY
features the data can actually support (no time-velocity, no graph). Each
feature maps to an IOB mule typology so the downstream rule engine stays
explainable.

Outputs:
  output/account_features.csv
"""
from __future__ import annotations
import argparse
import numpy as np
import pandas as pd
from common import load, OUT, REF_DATE, has_time_axis, has_counterparty
import os


def _temporal_features(df: pd.DataFrame, index: pd.Index) -> pd.DataFrame:
    """Timing signals — only meaningful when TRAN_DATE carries a real spread.

    Captures velocity, bursts, and pass-through *timing* (how fast credits are
    swept back out), none of which the constant-date real file can support.
    """
    t = df[["ACID", "TRAN_DATE", "PART_TRAN_TYPE"]].dropna(subset=["TRAN_DATE"]).copy()
    out = pd.DataFrame(index=index)
    active_days, per_active_day, max_1h, sweep_lat = {}, {}, {}, {}
    for acid, g in t.groupby("ACID"):
        ts = g["TRAN_DATE"].sort_values()
        active_days[acid] = ts.dt.normalize().nunique()
        span_days = max((ts.max() - ts.min()).total_seconds() / 86400.0, 1e-9)
        per_active_day[acid] = len(ts) / max(active_days[acid], 1)
        # busiest 1h window (two-pointer over sorted epoch seconds)
        secs = ts.astype("int64").to_numpy() / 1e9
        j, best = 0, 0
        for i in range(len(secs)):
            while secs[i] - secs[j] > 3600:
                j += 1
            best = max(best, i - j + 1)
        max_1h[acid] = best
        # median hours from each credit to the next debit (pass-through latency)
        gg = g.sort_values("TRAN_DATE")
        deb = gg[gg["PART_TRAN_TYPE"] == "D"]["TRAN_DATE"].to_numpy()
        lats = []
        for ct in gg[gg["PART_TRAN_TYPE"] == "C"]["TRAN_DATE"].to_numpy():
            nxt = deb[deb > ct]
            if len(nxt):
                lats.append((nxt[0] - ct) / np.timedelta64(1, "h"))
        sweep_lat[acid] = float(np.median(lats)) if lats else float(span_days * 24)
    out["active_days"] = pd.Series(active_days)
    out["txn_per_active_day"] = pd.Series(per_active_day)
    out["max_txn_1h"] = pd.Series(max_1h)
    out["sweep_latency_hr"] = pd.Series(sweep_lat)
    return out


def _graph_features(df: pd.DataFrame, index: pd.Index) -> pd.DataFrame:
    """Money-flow graph centrality — only when counterparty edges exist.

    Directed edge sender->receiver: a debit row is ACID->BENEFICIARY, a credit row
    is BENEFICIARY->ACID. Features are read back only for population accounts.
    """
    import networkx as nx

    e = df.dropna(subset=["BENEFICIARY_ACID"]).copy()
    src = np.where(e["PART_TRAN_TYPE"].to_numpy() == "D", e["ACID"], e["BENEFICIARY_ACID"])
    dst = np.where(e["PART_TRAN_TYPE"].to_numpy() == "D", e["BENEFICIARY_ACID"], e["ACID"])
    G = nx.DiGraph()
    for s, d, w in zip(src, dst, e["TRAN_AMT"].fillna(0.0).to_numpy()):
        if G.has_edge(s, d):
            G[s][d]["weight"] += float(w)
        else:
            G.add_edge(s, d, weight=float(w))

    pr = nx.pagerank(G, weight="weight") if G.number_of_edges() else {}
    k = min(G.number_of_nodes(), 150) or 1
    btw = nx.betweenness_centrality(G, k=k, weight="weight", seed=42) if G.number_of_nodes() > 2 else {}

    out = pd.DataFrame(index=index)
    out["n_senders"] = pd.Series({n: G.in_degree(n) for n in index if n in G})
    out["n_recipients"] = pd.Series({n: G.out_degree(n) for n in index if n in G})
    out["pagerank"] = pd.Series({n: pr.get(n, 0.0) for n in index})
    out["betweenness"] = pd.Series({n: btw.get(n, 0.0) for n in index})
    out["fan_in_out_ratio"] = out["n_senders"] / out["n_recipients"].replace(0, np.nan)
    return out.fillna(0.0)


def build_features(df: pd.DataFrame) -> pd.DataFrame:
    credits = df[df["PART_TRAN_TYPE"] == "C"]
    debits = df[df["PART_TRAN_TYPE"] == "D"]

    g = df.groupby("ACID")
    gc = credits.groupby("ACID")
    gd = debits.groupby("ACID")

    feat = pd.DataFrame(index=g.size().index)
    feat["n_txn"] = g.size()
    feat["n_credit"] = gc.size().reindex(feat.index).fillna(0)
    feat["n_debit"] = gd.size().reindex(feat.index).fillna(0)

    feat["amt_in"] = gc["TRAN_AMT"].sum().reindex(feat.index).fillna(0.0)
    feat["amt_out"] = gd["TRAN_AMT"].sum().reindex(feat.index).fillna(0.0)
    feat["turnover"] = feat["amt_in"] + feat["amt_out"]

    # --- pass-through: money in ~ money out, little retained ---
    feat["passthrough_ratio"] = feat["amt_out"] / feat["amt_in"].replace(0, np.nan)
    feat["passthrough_ratio"] = feat["passthrough_ratio"].fillna(0.0)
    feat["net_retention"] = (feat["amt_in"] - feat["amt_out"]) / feat["amt_in"].replace(0, np.nan)
    feat["net_retention"] = feat["net_retention"].fillna(0.0)

    # --- fan-in aggregation proxy: many incoming credits, few pay-outs ---
    # (true fan-in needs senders; credit multiplicity is an honest proxy)
    feat["credit_to_debit_ratio"] = feat["n_credit"] / feat["n_debit"].replace(0, np.nan)
    feat["credit_to_debit_ratio"] = feat["credit_to_debit_ratio"].fillna(feat["n_credit"])

    # --- amount profile ---
    feat["amt_mean"] = g["TRAN_AMT"].mean()
    feat["amt_std"] = g["TRAN_AMT"].std().fillna(0.0)
    feat["amt_max"] = g["TRAN_AMT"].max()
    feat["amt_cv"] = feat["amt_std"] / feat["amt_mean"].replace(0, np.nan)
    feat["amt_cv"] = feat["amt_cv"].fillna(0.0)
    feat["micro_credit_share"] = (
        credits.assign(m=(credits["TRAN_AMT"] < 100).astype(int))
        .groupby("ACID")["m"].mean().reindex(feat.index).fillna(0.0)
    )

    # --- structuring: txns just under the Rs 50k CTR line ---
    df_struct = df.assign(s=((df["TRAN_AMT"] >= 45000) & (df["TRAN_AMT"] < 50000)).astype(int))
    feat["n_structuring"] = df_struct.groupby("ACID")["s"].sum().reindex(feat.index).fillna(0)

    # --- tenure / new-account burst ---
    opn = g["ACCT_OPN_DATE"].first()
    feat["account_age_days"] = (REF_DATE - opn).dt.days
    # txns per 100 days of account life (burst if young account is very active)
    feat["txn_per_100d"] = feat["n_txn"] / (feat["account_age_days"].clip(lower=1) / 100.0)

    # --- channel & lien ---
    upi = df.assign(u=(df["channel"] == "UPI").astype(int))
    feat["upi_share"] = upi.groupby("ACID")["u"].mean().reindex(feat.index).fillna(0.0)
    feat["lien_ratio"] = g["LIEN_AMT"].max() / feat["turnover"].replace(0, np.nan)
    feat["lien_ratio"] = feat["lien_ratio"].fillna(0.0)

    # --- Tier-B features, only where the data supports them (synthetic) ---------
    # Gated so the real 19-account path produces an unchanged feature table.
    if has_time_axis(df):
        feat = feat.join(_temporal_features(df, feat.index))
    if has_counterparty(df):
        feat = feat.join(_graph_features(df, feat.index))
    # carry ground-truth label + provenance through for the supervised stage
    for col in ("is_mule", "typology", "source"):
        if col in df.columns:
            feat[col] = g[col].first()

    feat = feat.reset_index().rename(columns={"index": "ACID"})
    return feat


def out_path(source: str) -> str:
    suffix = "" if source == "real" else f"_{source}"
    return os.path.join(OUT, f"account_features{suffix}.csv")


def main(source: str = "real") -> None:
    df = load(source)
    feat = build_features(df)
    path = out_path(source)
    feat.to_csv(path, index=False)
    print(feat.round(2).to_string(index=False))
    print(f"\n[01] wrote {path}  ({len(feat)} accounts x {feat.shape[1]-1} features)")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--source", choices=["real", "synthetic", "both"], default="real")
    args = ap.parse_args()
    main(args.source)
