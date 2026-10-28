#!/usr/bin/env bash
# Run the Tier-B pipeline on the jury-approved SYNTHETIC scenario dataset.
# Unlocks supervised (XGBoost) + temporal + graph-centrality features and real
# ROC-AUC/PR-AUC validation. The real Tier-A pipeline (run_all.sh) is untouched.
#
# Requires the OpenMP runtime for xgboost — on macOS: `brew install libomp`.
# Usage:  bash ml_pipeline/run_synthetic.sh
set -euo pipefail
cd "$(dirname "$0")"

echo "== generate synthetic scenario =="   && python synth/generate.py
echo "== 00 synthetic data-quality gate =="  && python 00_eda_quality.py --source synthetic
echo "== 01 features (temporal + graph) =="   && python 01_features.py --source synthetic
echo "== 02 scoring (rules + IsoForest + XGBoost) ==" && python 02_score.py --source synthetic
echo "== 03 SHAP (XGBoost TreeExplainer) =="   && python 03_explain.py --source synthetic
echo "== 04 supervised validation =="          && python 04_validate.py --source synthetic
echo "== 05 synthetic report =="               && python 05_report.py --source synthetic
echo "== 06 ROC / PR curves =="                && python 06_chart.py --source synthetic
echo "Done. See ml_pipeline/output/*_synthetic.* and roc_pr_synthetic.png"
