#!/usr/bin/env bash
# Run the full AML Shield Tier-A pipeline in order.
# Usage:  bash ml_pipeline/run_all.sh
set -euo pipefail
cd "$(dirname "$0")"

echo "== 00 data quality gate =="   && python 00_eda_quality.py
echo "== 01 feature engineering ==" && python 01_features.py
echo "== 02 hybrid scoring =="       && python 02_score.py
echo "== 03 explainability (SHAP) ==" && python 03_explain.py
echo "== 04 validation =="           && python 04_validate.py
echo "== 05 final report =="         && python 05_report.py
echo "== 06 results chart =="        && python 06_chart.py
echo "Done. See ml_pipeline/output/"
