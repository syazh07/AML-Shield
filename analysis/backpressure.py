"""
Reviewer backpressure model for AML Shield.

Anchored to WHITEPAPER.md so every number on stage is consistent and citable.

Thesis: mule accounts are rare, so even a high-sensitivity model yields alert
queues that are mostly false positives (the base-rate fallacy). The binding
constraint is human review time, not model accuracy. Shrinking per-alert review
time (the workstation / copilot) beats a hard model improvement.

All inputs are ILLUSTRATIVE and tunable -- edit the ASSUMPTIONS block and re-run.
Section 1 reproduces the whitepaper's base-rate table (per 100k transactions).
Sections 2-3 reproduce its staffing math (per 10k alerts/day) and compare the
two levers.

Run:  python analysis/backpressure.py
"""
from __future__ import annotations
import os
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

HERE = os.path.dirname(os.path.abspath(__file__))

# --------------------------------------------------------------------------- #
# ASSUMPTIONS  (tunable; defaults match WHITEPAPER.md)                          #
# --------------------------------------------------------------------------- #
SENSITIVITY = 0.95            # recall: share of true mules caught
FPR = 0.03                    # false-positive rate (whitepaper canonical = 3%)

# Section 1 - precision vs base rate (whitepaper Table 1)
TXN_PER_DAY = 100_000
BASE_RATES = [0.001, 0.01, 0.10, 0.50]   # 0.1% is the FinCrime reality

# Sections 2-3 - staffing (whitepaper: 10k alerts/day, 90% false positive)
ALERTS_PER_DAY = 10_000
INDUSTRY_FP_RATE = 0.90
REVIEW_MIN_LEGACY = 30        # whitepaper L1 median 30-45 min
COPILOT_PRODUCTIVITY_GAIN = 0.70   # whitepaper: AI copilots up to 70%
MODEL_FP_REDUCTION = 0.50     # a hard model-only win: cut false positives 50%
ANALYST_HOURS_PER_DAY = 8     # productive review hours per analyst per day

REVIEW_MIN_WORKSTATION = round(REVIEW_MIN_LEGACY * (1 - COPILOT_PRODUCTIVITY_GAIN))


def confusion(n, base_rate, sensitivity, fpr):
    positives = n * base_rate
    negatives = n - positives
    tp = positives * sensitivity
    fp = negatives * fpr
    return tp, fp


def fmt(n):
    return f"{n:,.0f}"


def build_report():
    L = []
    add = L.append
    add("# Reviewer Backpressure Model\n")
    add("*Numbers anchored to `WHITEPAPER.md`. All inputs live in the ASSUMPTIONS "
        "block of `analysis/backpressure.py` and are meant to be adjusted.*\n")

    # ---- Section 1: precision vs base rate (reproduces whitepaper Table 1) ----
    add("## 1. Precision collapses when the target is rare (base-rate fallacy)")
    add(f"Per **{fmt(TXN_PER_DAY)} transactions/day**, model held at "
        f"**{SENSITIVITY:.0%} sensitivity** and **{FPR:.0%} false-positive rate**; "
        f"only the base rate of illicit activity changes:\n")
    add("| Base rate | True positives | False positives | Total alerts | "
        "**Precision (PPV)** |")
    add("|---|---|---|---|---|")
    for br in BASE_RATES:
        tp, fp = confusion(TXN_PER_DAY, br, SENSITIVITY, FPR)
        alerts = tp + fp
        ppv = tp / alerts if alerts else 0
        add(f"| {br:.1%} | {fmt(tp)} | {fmt(fp)} | {fmt(alerts)} | **{ppv:.1%}** |")
    add("\n> At the FinCrime-real **0.1%** base rate, precision is **~3.1%** -- "
        "**~97 of every 100 alerts are false**. This matches the industry's "
        "documented 85-95% false-positive rate. You cannot out-model arithmetic.\n")

    # ---- Section 2: the staffing burden (reproduces whitepaper staffing table) ----
    add("## 2. What that does to the review team")
    fp_alerts = ALERTS_PER_DAY * INDUSTRY_FP_RATE
    wasted_hours = fp_alerts * REVIEW_MIN_LEGACY / 60
    fte_wasted = wasted_hours / ANALYST_HOURS_PER_DAY
    add(f"Per **{fmt(ALERTS_PER_DAY)} alerts/day** at the industry "
        f"**{INDUSTRY_FP_RATE:.0%}** false-positive rate, **{REVIEW_MIN_LEGACY} min** "
        f"per review:\n")
    add(f"- False-positive alerts/day: **{fmt(fp_alerts)}**")
    add(f"- Analyst-hours/day wasted on noise: **{fmt(wasted_hours)}**")
    add(f"- Equivalent staffing on noise alone: **{fmt(fte_wasted)} full-time "
        f"analysts** ({ANALYST_HOURS_PER_DAY}h/day)\n")

    # ---- Section 3: the two levers ----
    add("## 3. Two ways to fix it -- and which wins")
    tp_alerts = ALERTS_PER_DAY - fp_alerts

    def load(alerts, minutes):
        hrs = alerts * minutes / 60
        return hrs, hrs / ANALYST_HOURS_PER_DAY

    h_legacy, fte_legacy = load(ALERTS_PER_DAY, REVIEW_MIN_LEGACY)
    alerts_model = tp_alerts + fp_alerts * (1 - MODEL_FP_REDUCTION)
    h_model, fte_model = load(alerts_model, REVIEW_MIN_LEGACY)
    h_ws, fte_ws = load(ALERTS_PER_DAY, REVIEW_MIN_WORKSTATION)

    add(f"Legacy operating point: {fmt(ALERTS_PER_DAY)} alerts/day, "
        f"{REVIEW_MIN_LEGACY} min each.\n")
    add("| Strategy | Alerts/day | Review-hours/day | Analysts (FTE) | Saving |")
    add("|---|---|---|---|---|")
    add(f"| Legacy tooling ({REVIEW_MIN_LEGACY} min) | {fmt(ALERTS_PER_DAY)} | "
        f"{fmt(h_legacy)} | {fmt(fte_legacy)} | -- |")
    add(f"| **Hard model win** (-{MODEL_FP_REDUCTION:.0%} false positives, still "
        f"{REVIEW_MIN_LEGACY} min) | {fmt(alerts_model)} | {fmt(h_model)} | "
        f"{fmt(fte_model)} | {1-h_model/h_legacy:.0%} |")
    add(f"| **AML Shield workstation** (same alerts, {REVIEW_MIN_WORKSTATION} min = "
        f"-{COPILOT_PRODUCTIVITY_GAIN:.0%} review time) | {fmt(ALERTS_PER_DAY)} | "
        f"{fmt(h_ws)} | {fmt(fte_ws)} | {1-h_ws/h_legacy:.0%} |")
    add(f"\n- A hard model win (halving false positives) saves "
        f"**{1-h_model/h_legacy:.0%}** of review hours.")
    add(f"- The workstation saves **{1-h_ws/h_legacy:.0%}** -- on the *same* alerts, "
        f"no model change -- a **{REVIEW_MIN_LEGACY/REVIEW_MIN_WORKSTATION:.1f}x** "
        f"throughput gain, matching the whitepaper's cited ~70% copilot productivity.")
    add("- They **stack**: HSBC + Google Cloud paired explainable workflows with ML "
        "for **2-4x more true positives and >60% fewer false positives**.\n")
    add("> Detection is a plug-in. Review capacity is the business. AML Shield "
        "attacks the term that dominates the cost.")

    return "\n".join(L) + "\n", (h_legacy, h_model, h_ws)


def make_chart(hours):
    h_legacy, h_model, h_ws = hours
    labels = ["Legacy\n(30 min)", "Hard model win\n(-50% false pos.)",
              "AML Shield\n(9 min, -70%)"]
    vals = [h_legacy, h_model, h_ws]
    colors = ["#8a94a6", "#8a94a6", "#c1440e"]
    INK = "#333333"

    fig, ax = plt.subplots(figsize=(7.5, 4.6))
    bars = ax.bar(labels, vals, color=colors, width=0.6, zorder=3)
    ax.set_ylim(0, max(vals) * 1.15)
    for b, v in zip(bars, vals):
        ax.text(b.get_x() + b.get_width()/2, v, f"{v:,.0f} h", ha="center",
                va="bottom", fontsize=10, color=INK)
    ax.set_ylabel("Review-hours per day (per 10k alerts)", fontsize=10, color=INK)
    ax.set_title("Review-hours: the workstation beats a hard model win",
                 fontsize=12, color=INK, pad=12)
    ax.grid(axis="y", color="#e6e6e6", zorder=0)
    ax.set_axisbelow(True)
    for s in ["top", "right"]:
        ax.spines[s].set_visible(False)
    ax.tick_params(length=0)
    fig.tight_layout()
    path = os.path.join(HERE, "backpressure_chart.png")
    fig.savefig(path, dpi=150, bbox_inches="tight")
    return path


def main():
    report, hours = build_report()
    md_path = os.path.join(HERE, "backpressure_table.md")
    with open(md_path, "w") as f:
        f.write(report)
    chart = make_chart(hours)
    print(report)
    print(f"[backpressure] wrote {md_path}")
    print(f"[backpressure] wrote {chart}")


if __name__ == "__main__":
    main()
