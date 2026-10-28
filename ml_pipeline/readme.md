# AML Shield — ML Plan (v2, data-grounded) + Comparison

> Purpose: an independent modeling plan built **from the actual sample data**, then a
> head-to-head comparison with the existing `ml_plan.md`, then a recommended "best model".
> The `project/` folder is intentionally ignored.

---

## 0. What the sample data actually is (ground truth check)

I profiled `mule_sample_data.csv` before planning. This changes the modeling options significantly.

| Fact | Value | Consequence for modeling |
|---|---|---|
| Rows / accounts | 2000 transactions, **19 accounts** (ACID), 19 CIF_IDs (1:1) | Account-level supervised ML is statistically meaningless (N=19). |
| Label column | **None** | No supervised training without synthesizing labels. |
| `TRAN_DATE` | **All identical** = `19/05/2026 18:30` | No real time axis → **pass-through timing, velocity-per-hour, impossible-travel, unusual-hours are NOT computable**. Only row-order and counts survive. |
| Counterparty / beneficiary | **No such column** | Cannot build an account→account money-flow graph. **PageRank / betweenness / fan-in-fan-out are not derivable from this file.** |
| `PART_TRAN_TYPE` | C=1837 credits, D=163 debits | Direction is available (money in vs out) — this is the strongest usable signal. |
| `channel` | UPI 98.5% (1971), rest NEFT/IMPS/MB/BNA/ATM | Channel is nearly constant → weak feature here. |
| `TRAN_AMT` | min 1, max 100,000, median ~500, mean 1694 | Many tiny amounts; only 2 txns in the 45k–50k structuring band; 0 txns ≥ ₹10 lakh. |
| `TRAN_TYPE` / `TRAN_SUB_TYPE` | Constant (`T` / `CI`) | Zero information — drop. |
| `balance` | −213,606 to 183,494, doesn't reconcile with amounts | Data is synthetic/shuffled → treat balance features cautiously. |
| `LIEN_AMT` | Median == max (92,993.72) | Suspicious constant — likely injected; use as-is but flag. |
| `customer_age` | 1715 of 2000 = age 30 | Mostly imputed/default → weak feature. |
| Concentration | 1 account = **1704 of 2000 txns**, 1691 credits vs 13 debits | Textbook aggregator/collector mule: heavy fan-in, few large pay-outs. |

**Bottom line:** the sample supports a **transaction- and account-level behavioral model**, *not* the
full graph + temporal-sequence + supervised platform described in `problem_statement.md`. Any plan
that promises graph centrality or LSTM sequences *on this file* is describing the roadmap, not the POC.

---

## 1. My proposed approach — two honest tiers

### Tier A — What we can build NOW (this file)
An **explainable hybrid detector**: transparent rule-scoring **fused with** an unsupervised anomaly
model, producing a 0–100 composite risk score with an additive reason breakdown. No fabricated labels
drive a "real" classifier.

### Tier B — Fully Implemented on Synthetic Data
Per mentor guidance, we generated a robust synthetic scenario (`synth/generate.py`) providing the missing labels, timestamps, and counterparty edges. This unlocks our fully supervised XGBoost model with graph centrality (PageRank/Betweenness) and temporal features. You can run this pipeline using `bash run_synthetic.sh`.

- **Supervised XGBoost** on ground-truth labels → **ROC-AUC 0.996, PR-AUC 0.982, 5-fold CV 0.997 ± 0.004**
  (precision 0.94 / recall 0.92), with TreeExplainer SHAP.
- **Temporal features** (velocity, pass-through timing, bursts) from real synthetic timestamps.
- **Graph centrality** (PageRank, betweenness, fan-in/out via `networkx`) from counterparty edges.

Metrics are reported as **capability, not production performance** (the synthetic data has a known
generative process). The real 19-account sample remains the unsupervised **reality anchor**, and the
statements below about *this file* (constant date, no counterparty, etc.) still describe the real
extract. LSTM autoencoder stays roadmap (needs real per-transaction sequences). Run: `bash run_synthetic.sh`.

---

## 2. Pipeline (Tier A)

### Step 1 — Data quality gate (`00_eda_quality.py`)
Assert the realities above (constant date, constant tran-type, age default, balance non-reconciliation),
emit a short data-quality report, and drop zero-information columns. This prevents silently "modeling"
noise.

### Step 2 — Account-level feature engineering (`01_features.py`)
Aggregate the 2000 transactions to 19 account rows using **only computable** features:

- **Flow / pass-through (count + value):** `amt_out/amt_in` ratio, net retention =
  `(amt_in − amt_out)/amt_in`, credit-count vs debit-count skew. (This replaces time-based
  pass-through, which the data can't support.)
- **Fan-in proxy:** number/volume of incoming credits per account (real fan-in needs senders; here we
  use credit multiplicity as a proxy and label it honestly).
- **Structuring:** count of txns in ₹45k–₹49,999 band; count just under ₹10 lakh; near-round-number rate.
- **Amount profile:** mean, std, max, coefficient of variation, share of micro-txns (<₹100), share of
  large (≥₹50k).
- **Tenure / dormancy:** days between `ACCT_OPN_DATE` and the (single) `TRAN_DATE`; "new-account burst"
  flag = young account with high txn count.
- **Channel & lien:** UPI share, LIEN_AMT ratio to turnover.

### Step 3 — Model: rules ⊕ anomaly (`02_score.py`)
1. **Transparent weighted rule score (anchor).** Each IOB pattern → a bounded points contribution
   (e.g. pass-through +28, structuring +18, new-account burst +15…). Fully auditable for RBI.
2. **Unsupervised anomaly score (discovery).** **Isolation Forest** on the standardized feature matrix
   (primary), optionally corroborated by **Local Outlier Factor**. Run it **twice**: at account level
   (19 rows — coarse) and at **transaction level (2000 rows — where anomaly detection actually has
   enough samples)**, then roll transaction anomalies up per account.
3. **Fusion → composite 0–100:** `Risk = clip(w_r·RuleScore + w_a·AnomalyScore)`, with the rule term
   weighted higher *because N is tiny* and anomaly models are unstable at N=19.

### Step 4 — Explainability (`03_explain.py`)
- **Rule contributions** are additive by construction → native "device/pass-through/structuring +X pts"
  breakdown (matches the SHAP-style narrative in the problem statement).
- **SHAP** on the Isolation Forest for the anomaly component.
- Emit a plain-English reason string per flagged account.

### Step 5 — Validation without labels (`04_validate.py`)
Since there are no labels, we **cannot** report precision/recall honestly on real data. Instead:
- **Synthetic-mule injection:** plant known pass-through / structuring accounts, confirm they surface in
  the top-N (recall on planted positives).
- **Sensitivity / stability** of ranking to weights and Iso-Forest seed.
- **Manual top-N review** table for a human analyst.

### Step 6 — Output (`05_report.py`)
`flagged_mule_accounts.csv`: `ACID, Risk_Score, Is_Flagged, Top_Reasons, Rule_Breakdown, Anomaly_Score`.

---

## 3. Comparison with existing `ml_plan.md`

| Dimension | `ml_plan.md` (existing) | My plan (v2) | Who's right / why |
|---|---|---|---|
| No-label handling | Weak supervision → **train XGBoost/RF on rule-generated labels** | Rules **anchor**; unsupervised anomaly for discovery; **no classifier trained on rule labels** | **v2.** Training a classifier on rule labels with N=19 just re-learns the rules and overfits — SHAP on it is misleading. |
| Graph (PageRank/betweenness, fan-in/out) | Full Step 2 with `networkx` on this data | Declared **not buildable** from this file (no counterparty); moved to Tier B with a plug-in schema | **v2.** The file has no destination account — there are no edges to run centrality on. |
| Time-based features (velocity, pass-through timing) | "High frequency in a short time" | Replaced with **count/ratio** features; timing deferred | **v2.** `TRAN_DATE` is constant — no time axis exists. |
| Isolation Forest | Yes (secondary to XGBoost) | Yes — **promoted to the primary ML model**, run at txn level too | Both include it; v2 leans on the one model the data can actually support. |
| SHAP explainability | Yes | Yes + additive rule breakdown | **Agree** — keep. |
| Sample-size realism | Not addressed | Explicit (N=19) | v2 adds. |
| Validation w/o labels | Not specified | Synthetic injection + sensitivity + manual review | v2 adds. |
| Composite 0–100 score | Yes | Yes | **Agree** — keep. |
| Clean 4-step layout | **Strong** | Kept, extended to 6 | Keep the existing plan's clarity. |

**What `ml_plan.md` gets right and I keep:** the weak-supervision framing, Isolation Forest, SHAP, the
composite 0–100 score, the tidy staged pipeline, and the CSV output contract.

**Where it over-promises against this data:** graph centrality, time-velocity features, and treating a
rule-labeled XGBoost as a genuine learned model.

---

## 4. Recommended "best model" (synthesis)

**Primary (ship on the sample data): Explainable Hybrid = Weighted Rule Engine ⊕ Isolation Forest → 0–100 composite, with additive + SHAP explanations.**

- Rule engine = auditable, regulator-friendly, works at N=19, encodes IOB-specific typologies.
- Isolation Forest = the single unsupervised ML model this data can legitimately support; run at
  transaction level (2000 rows) for statistical stability, rolled up per account.
- Fusion gives one 0–100 score; explanations satisfy the "every alert explained" requirement.

**Synthetic tier (Unlocked via `run_synthetic.sh`):**
- **XGBoost / Random Forest** ← Trained on *confirmed-mule labels* from the synthetic scenario.
- **Neo4j graph (Louvain / PageRank / betweenness)** ← Computed using *counterparty edges* generated in the scenario.
- **Temporal Features** ← Computed using *real per-transaction timestamps*.

**One-line recommendation:** Anchor on rules + Isolation Forest for the raw sample data; run `bash run_synthetic.sh` to demonstrate the full XGBoost/Graph pipeline on the mentor-approved synthetic data.

---

## 5. Locked decisions

1. **Scope: Dual Pipeline** — We provide `run_all.sh` for Tier A (rules ⊕ Isolation Forest on the raw sample data) and `run_synthetic.sh` for Tier B (rules ⊕ Isolation Forest ⊕ XGBoost ⊕ Graph on the synthetic data). Both approaches are fully functional and ready for the jury.
2. **Flagging unit: account-level** (matches "mule account").
3. **Alert threshold: fixed score cutoff** (e.g. ≥ 60/100) — stable and regulator-explainable;
   top-K% rejected as too fragile at N=19.
