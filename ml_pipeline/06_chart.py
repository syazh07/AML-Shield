"""
Stage 06 - Results chart for the jury deck.

A sorted horizontal bar chart of composite risk per account (magnitude +
binary flagged/not-flagged status), with the fixed cutoff drawn as a labeled
reference line. Static PNG so it embeds cleanly in slides / GitHub markdown.

Outputs:
  output/risk_ranking.png
"""
from __future__ import annotations
import argparse
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Patch
from common import OUT, FLAG_THRESHOLD, short
import os

# status colors (reserved) - flagged vs below-threshold; recessive ink for text
C_FLAG = "#c1440e"     # serious/critical
C_OK = "#8a94a6"       # muted slate for below-threshold
INK = "#333333"
GRID = "#e6e6e6"


def main() -> None:
    rep = pd.read_csv(os.path.join(OUT, "flagged_mule_accounts.csv"))
    rep = rep.sort_values("Risk_Score", ascending=True)  # ascending -> highest on top
    labels = rep["ACID_short"] if "ACID_short" in rep else rep["Account"]
    scores = rep["Risk_Score"]
    flagged = rep["Risk_Score"] >= FLAG_THRESHOLD
    colors = [C_FLAG if f else C_OK for f in flagged]

    fig, ax = plt.subplots(figsize=(9, 6.5))
    y = range(len(rep))
    ax.barh(list(y), scores, color=colors, height=0.68, zorder=3)

    # value labels at bar ends
    for yi, s in zip(y, scores):
        ax.text(s + 1.0, yi, f"{s:.0f}", va="center", ha="left",
                fontsize=9, color=INK, zorder=4)

    # threshold line
    ax.axvline(FLAG_THRESHOLD, color=INK, linestyle="--", linewidth=1.4, zorder=2)
    ax.text(FLAG_THRESHOLD + 0.5, len(rep) - 0.3,
            f"flag cutoff = {FLAG_THRESHOLD:.0f}", fontsize=9,
            color=INK, ha="left", va="top")

    ax.set_yticks(list(y))
    ax.set_yticklabels(labels, fontsize=9)
    ax.set_xlabel("Composite risk score (0-100)", fontsize=10, color=INK)
    ax.set_xlim(0, 100)
    ax.set_title("AML Shield - account risk ranking (19 accounts)",
                 fontsize=13, color=INK, pad=12)

    ax.grid(axis="x", color=GRID, linewidth=1, zorder=0)
    ax.set_axisbelow(True)
    for spine in ["top", "right", "left"]:
        ax.spines[spine].set_visible(False)
    ax.tick_params(length=0)

    n_flag = int(flagged.sum())
    ax.legend(handles=[
        Patch(color=C_FLAG, label=f"Flagged ({n_flag})"),
        Patch(color=C_OK, label=f"Below cutoff ({len(rep)-n_flag})"),
    ], loc="lower right", frameon=False, fontsize=9)

    fig.tight_layout()
    path = os.path.join(OUT, "risk_ranking.png")
    fig.savefig(path, dpi=150, bbox_inches="tight")
    print(f"[06] wrote {path}")


def synthetic_chart() -> None:
    """ROC + Precision-Recall curves for the supervised model on the synthetic
    scenario — the visual proof of the metrics in validation_report_synthetic.md."""
    from sklearn.metrics import (average_precision_score, precision_recall_curve,
                                 roc_auc_score, roc_curve)

    scores = pd.read_csv(os.path.join(OUT, "account_scores_synthetic.csv"))
    y = scores["is_mule"].astype(int).to_numpy()
    p = (scores["supervised_score"] / 100.0).to_numpy()

    fpr, tpr, _ = roc_curve(y, p)
    prec, rec, _ = precision_recall_curve(y, p)
    roc_auc = roc_auc_score(y, p)
    pr_auc = average_precision_score(y, p)

    fig, (a1, a2) = plt.subplots(1, 2, figsize=(11, 4.6))
    a1.plot(fpr, tpr, color=C_FLAG, lw=2, zorder=3, label=f"XGBoost (AUC={roc_auc:.3f})")
    a1.plot([0, 1], [0, 1], color=C_OK, ls="--", lw=1.2, zorder=2)
    a1.set_xlabel("False positive rate"); a1.set_ylabel("True positive rate")
    a1.set_title("ROC — synthetic scenario", color=INK)
    a1.legend(loc="lower right", frameon=False, fontsize=9)

    a2.plot(rec, prec, color=C_FLAG, lw=2, zorder=3, label=f"XGBoost (AP={pr_auc:.3f})")
    a2.axhline(y.mean(), color=C_OK, ls="--", lw=1.2, zorder=2,
               label=f"baseline ({y.mean():.2f})")
    a2.set_xlabel("Recall"); a2.set_ylabel("Precision")
    a2.set_title("Precision-Recall — synthetic scenario", color=INK)
    a2.legend(loc="lower left", frameon=False, fontsize=9)

    for ax in (a1, a2):
        ax.set_xlim(-0.02, 1.02); ax.set_ylim(-0.02, 1.02)
        ax.grid(color=GRID, linewidth=1, zorder=0); ax.set_axisbelow(True)
        for sp in ["top", "right"]:
            ax.spines[sp].set_visible(False)
        ax.tick_params(length=0)

    fig.suptitle("Supervised capability on labelled synthetic data "
                 "(known generative process — not production performance)",
                 fontsize=10, color=INK)
    fig.tight_layout()
    path = os.path.join(OUT, "roc_pr_synthetic.png")
    fig.savefig(path, dpi=150, bbox_inches="tight")
    print(f"[06] wrote {path}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--source", choices=["real", "synthetic"], default="real")
    args = ap.parse_args()
    if args.source == "synthetic":
        synthetic_chart()
    else:
        main()
