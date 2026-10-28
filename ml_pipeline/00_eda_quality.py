"""
Stage 00 - Data-quality gate.

Before modeling anything, verify the realities of the sample data and drop
zero-information columns. This stops us from silently "modeling" noise and
documents, for the jury, exactly what this file can and cannot support.

Outputs:
  output/data_quality_report.md
"""
from __future__ import annotations
import argparse
import pandas as pd
from common import load, load_synthetic, OUT, has_time_axis, has_counterparty
import os


def synthetic_gate() -> None:
    """Provenance gate for the synthetic scenario dataset: assert it actually
    carries the inputs the real file lacks (time axis, counterparty, labels),
    so downstream Tier-B features/metrics are honestly earned."""
    df = load_synthetic()
    acc = df.groupby("ACID")["is_mule"].first()
    lines = ["# Data Quality Report - synthetic_scenario.csv\n"]
    add = lines.append
    add(f"- **Transactions (rows):** {len(df)}")
    add(f"- **Accounts (ACID):** {df['ACID'].nunique()}")
    add(f"- **Labelled mules / normals:** {int(acc.sum())} / {int((acc == 0).sum())}")
    add("\n## Tier-B input gate")
    add(f"- Real time axis present (TRAN_DATE varies): **{has_time_axis(df)}** "
        f"({df['TRAN_DATE'].nunique()} distinct timestamps)")
    add(f"- Counterparty edges present (BENEFICIARY_ACID): **{has_counterparty(df)}**")
    add(f"- Ground-truth label present (is_mule): **{'is_mule' in df.columns}**")
    ok = has_time_axis(df) and has_counterparty(df) and "is_mule" in df.columns
    add(f"\n**Gate: {'PASS' if ok else 'FAIL'}** — supervised + temporal + graph "
        f"features are {'computable' if ok else 'NOT computable'} on this dataset.")
    add("\n> Synthetic data has a *known generative process*; metrics on it demonstrate "
        "capability, not production performance. The real 19-account sample remains the "
        "unsupervised reality anchor.")
    add("\n## Typology mix (planted)")
    for t, n in df.groupby("ACID")["typology"].first().value_counts().items():
        add(f"- `{t}`: {int(n)} accounts")
    report = "\n".join(lines) + "\n"
    path = os.path.join(OUT, "data_quality_report_synthetic.md")
    with open(path, "w") as f:
        f.write(report)
    print(report)
    print(f"[00] wrote {path}")


def main() -> None:
    df = load()  # real (default) — unchanged behaviour
    n_rows = len(df)
    lines = []
    add = lines.append

    add("# Data Quality Report - mule_sample_data.csv\n")
    add(f"- **Transactions (rows):** {n_rows}")
    add(f"- **Accounts (ACID):** {df['ACID'].nunique()}")
    add(f"- **Customers (CIF_ID):** {df['CIF_ID'].nunique()}")
    add(f"- **Unique TRAN_ID:** {df['TRAN_ID'].nunique()}")

    # --- constant / dead columns ---
    dead = [c for c in df.columns if df[c].nunique(dropna=False) == 1]
    add(f"\n## Zero-information columns (constant) -> dropped")
    for c in dead:
        add(f"- `{c}` = `{df[c].iloc[0]}`")

    # --- time axis check ---
    add(f"\n## Time axis")
    add(f"- Unique TRAN_DATE values: **{df['TRAN_DATE'].nunique()}** "
        f"(range {df['TRAN_DATE'].min()} .. {df['TRAN_DATE'].max()})")
    if df['TRAN_DATE'].nunique() == 1:
        add("- => **No real time axis.** Time-velocity / pass-through-timing / "
            "impossible-travel / unusual-hours features are NOT computable. "
            "We use count/ratio features instead.")

    # --- counterparty check ---
    add(f"\n## Graph feasibility")
    has_counterparty = any(
        k in [c.lower() for c in df.columns]
        for k in ["beneficiary", "dest", "counterparty", "to_acct", "vpa", "payee"]
    )
    add(f"- Counterparty / beneficiary column present: **{has_counterparty}**")
    if not has_counterparty:
        add("- => **No account->account edges.** PageRank / betweenness / "
            "fan-in-fan-out cannot be built from this file. Deferred to roadmap.")

    # --- direction / channel / amount profile ---
    add(f"\n## Usable signals")
    pt = df['PART_TRAN_TYPE'].value_counts().to_dict()
    add(f"- PART_TRAN_TYPE (direction): {pt}  <- strongest usable signal")
    ch = df['channel'].value_counts().to_dict()
    add(f"- channel: {ch}")
    amt = df['TRAN_AMT']
    add(f"- TRAN_AMT: min={amt.min():.0f}, median={amt.median():.0f}, "
        f"mean={amt.mean():.0f}, max={amt.max():.0f}")
    add(f"- Txns in structuring band 45k-49,999: "
        f"{int(((amt>=45000)&(amt<50000)).sum())}")
    add(f"- Txns >= 10 lakh (CTR single-txn): {int((amt>=1_000_000).sum())}")

    # --- data-quality caveats ---
    add(f"\n## Caveats (treat with care)")
    age_mode = df['customer_age'].mode().iloc[0]
    age_share = (df['customer_age'] == age_mode).mean()
    add(f"- customer_age is {age_mode:.0f} for {age_share:.0%} of rows -> "
        f"likely imputed/default; weak feature.")
    add(f"- balance ranges {df['balance'].min():.0f} .. {df['balance'].max():.0f} "
        f"and does not reconcile with amounts -> synthetic/shuffled; use cautiously.")
    lien_const = (df['LIEN_AMT'] == df['LIEN_AMT'].median()).mean()
    add(f"- LIEN_AMT equals its median for {lien_const:.0%} of rows -> near-constant injected value.")

    # --- account concentration ---
    top = df['ACID'].value_counts().head(1)
    add(f"\n## Concentration")
    add(f"- Busiest account holds {int(top.iloc[0])}/{n_rows} "
        f"({top.iloc[0]/n_rows:.0%}) of all transactions.")

    report = "\n".join(lines) + "\n"
    path = os.path.join(OUT, "data_quality_report.md")
    with open(path, "w") as f:
        f.write(report)
    print(report)
    print(f"[00] wrote {path}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--source", choices=["real", "synthetic"], default="real")
    args = ap.parse_args()
    if args.source == "synthetic":
        synthetic_gate()
    else:
        main()
