# AML Shield — Running the Project

How to start the **frontend**, the **backend**, and run the **ML pipeline**, plus
a reference for every file the pipeline produces. See
[DATA_FLOW.md](DATA_FLOW.md) for how these pieces fit together.

## Components & ports

| Component | Path | URL | Notes |
|---|---|---|---|
| Frontend (Vite + React) | `aml-dashboard/` | http://localhost:5173 | Proxies `/api` → backend :8000 |
| Backend (FastAPI) | `aml-dashboard/backend/` | http://localhost:8000 | Swagger at `/docs`, health at `/api/v1/health` |
| ML pipeline (batch) | `ml_pipeline/` | — | Writes reports to `ml_pipeline/output/` |

## Prerequisites

- **Node.js ≥ 18** (tested on v24)
- **Python ≥ 3.9** (backend supports 3.9/3.10 via `eval_type_backport`)
- **macOS + XGBoost:** `brew install libomp` (OpenMP runtime, needed by the
  synthetic pipeline only)

---

## 1. Backend — start this first

The frontend proxies API calls to the backend, so start it first.

```bash
cd aml-dashboard/backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env          # optional: add OPENAI_API_KEY for live STR + copilot
uvicorn app.main:app --reload --port 8000
```

- **Swagger UI:** http://localhost:8000/docs · **Health:** http://localhost:8000/api/v1/health
- **OpenAI key is optional.** Without it, non-showcase STR narratives and the
  copilot fall back to seed/summary text (the app still runs fully).
- **Database:** SQLite `aml_shield.db` is created and seeded (6 demo cases) on
  first start.
- **Reset the demo** to its clean seeded state: `python reset_db.py` (live reset
  if the server is up, else deletes the DB so the next start reseeds).
- **Optional live demo** (streams new cases/notifications into the running app):
  `python seeder.py`.

## 2. Frontend

```bash
cd aml-dashboard
npm install
npm run dev                   # http://localhost:5173
```

- Requires the backend running (it fetches `/api/v1/...`, proxied to :8000).
- Production build: `npm run build` → `dist/`; preview it with `npm run preview`.

## 3. ML pipeline

The pipeline is a batch job that writes reports to `ml_pipeline/output/`. It is
**independent of the backend** — the backend re-uses `ml_pipeline/common.py` at
runtime but never reads these output files (see [DATA_FLOW.md](DATA_FLOW.md) §1).

```bash
cd ml_pipeline
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
# macOS only, for the synthetic (XGBoost) path:  brew install libomp

bash run_all.sh               # REAL Tier-A:      stages 00→06 (default --source real)
bash run_synthetic.sh         # SYNTHETIC Tier-B: generate + 00→06 --source synthetic
```

- **Run one stage:** `python 02_score.py --source synthetic` (each of `00`–`06`
  takes `--source {real,synthetic,both}`; default `real`).
- **Real vs synthetic:** the real path (default) is the unsupervised anchor and is
  unchanged; the synthetic path adds supervised XGBoost + temporal + graph
  features. See [DATA_FLOW.md](DATA_FLOW.md) §2 and `ml_pipeline/readme.md`.

> The backend's runtime scoring only needs `pandas`/`numpy`/`scikit-learn` (already
> in the backend's requirements) — it does **not** need the pipeline's
> `shap`/`xgboost`/`networkx`. You can keep the two virtualenvs separate.

---

## 4. ML pipeline output reference (`ml_pipeline/output/`)

Real outputs are unsuffixed; the synthetic (Tier-B) run adds `*_synthetic.*`
counterparts. "Stage" is the script that writes the file.

| File | Stage | Contents |
|---|---|---|
| `data_quality_report.md` | 00 | Real‑file profile: row/account counts, dead columns, why time/graph features aren't computable on the real extract. |
| `account_features.csv` | 01 | One row per account (19). Cols: `ACID, n_txn, n_credit, n_debit, amt_in, amt_out, turnover, passthrough_ratio, net_retention, credit_to_debit_ratio, amt_mean, amt_std, amt_max, amt_cv, micro_credit_share, n_structuring, account_age_days, txn_per_100d, upi_share, lien_ratio`. |
| `account_scores.csv` | 02 | Per account: `ACID, rule_score, anomaly_score, composite_risk` (0–100). |
| `rule_contributions.csv` | 02 | Per‑account standalone risk (0–100) for each IOB rule: `pass_through, fan_in_aggregation, structuring, new_account_burst, micro_credit_flood, high_lien_ratio, rule_score`. |
| `explanations.csv` | 03 | Per account: `reason` (plain‑English rule drivers) + `top_anomaly_feature, top_anomaly_shap` (Isolation‑Forest SHAP). |
| `shap_feature_importance.csv` | 03 | Global SHAP importance for the anomaly model: `feature, mean_abs_shap`. |
| `validation_report.md` | 04 | Label‑free validation: planted mule‑vs‑normal separation + Isolation‑Forest seed stability (Kendall τ). |
| `flagged_mule_accounts.csv` | 05 | **The deliverable.** `Account, ACID, Risk_Score, Is_Flagged, Top_Reasons, Rule_Score, Anomaly_Score, Top_Anomaly_Feature`. |
| `risk_ranking.png` | 06 | Sorted horizontal bar chart of composite risk per account, with the flag cutoff line. |

### Synthetic (Tier‑B) outputs

| File | Stage | Contents |
|---|---|---|
| `data_quality_report_synthetic.md` | 00 | Provenance gate: confirms the synthetic set has timestamps + counterparty edges + labels; typology mix. |
| `account_features_synthetic.csv` | 01 | 330 accounts, all real‑path columns **plus** temporal (`active_days, txn_per_active_day, max_txn_1h, sweep_latency_hr`), graph (`n_senders, n_recipients, pagerank, betweenness, fan_in_out_ratio`), and `is_mule, typology, source`. |
| `account_scores_synthetic.csv` | 02 | `ACID, rule_score, anomaly_score, supervised_score, composite_risk, is_mule` (three‑way fusion). |
| `rule_contributions_synthetic.csv` | 02 | Same per‑rule breakdown as the real file, for the synthetic accounts. |
| `explanations_synthetic.csv` | 03 | `ACID, is_mule, top_supervised_feature, top_supervised_shap` (XGBoost TreeExplainer). |
| `shap_feature_importance_synthetic.csv` | 03 | Global XGBoost SHAP importance: `feature, mean_abs_shap`. |
| `validation_report_synthetic.md` | 04 | **Label‑based metrics:** ROC‑AUC, PR‑AUC, precision/recall/F1, confusion matrix, CV, + real‑anchor sanity check. |
| `flagged_mule_accounts_synthetic.csv` | 05 | `Account, ACID, Risk_Score, Is_Flagged, True_Mule, Correct, Rule_Score, Anomaly_Score, Supervised_Score, Top_Supervised_Feature`. |
| `roc_pr_synthetic.png` | 06 | ROC + Precision‑Recall curves for the supervised model. |

> Source datasets: `data/mule_sample_data.csv` (real) and, generated by
> `synth/generate.py`, `data/synthetic_scenario.csv` + `data/synthetic_accounts.csv`.

---

## 5. Typical local setup (all three, in order)

```bash
# terminal 1 — backend
cd aml-dashboard/backend && source .venv/bin/activate
uvicorn app.main:app --reload --port 8000

# terminal 2 — frontend
cd aml-dashboard && npm run dev            # open http://localhost:5173

# terminal 3 — pipeline (when you want fresh reports)
cd ml_pipeline && source .venv/bin/activate
bash run_all.sh && bash run_synthetic.sh
```

## 6. Troubleshooting

- **Dashboard loads but no data / network errors** → the backend isn't running on
  :8000. Start it first (the frontend proxies `/api` there).
- **`XGBoostError: libxgboost.dylib could not be loaded` (macOS)** → `brew install libomp`.
- **STR generation is slow / falls back to summary text** → that's the OpenAI call
  (or its 15s timeout fallback). Set `OPENAI_API_KEY` in `backend/.env` for live
  narratives; leave it unset to always use seed/summary text.
- **Port already in use** → change the port (`uvicorn … --port 8001`) and update
  the proxy target in `aml-dashboard/vite.config.js`, or free the port.
- **Want a clean demo** → `python reset_db.py` in `aml-dashboard/backend`.
