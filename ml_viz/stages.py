"""The seven-stage manifest — single source of truth for runner, server and UI.

Mirrors ml_pipeline/run_all.sh (real) and run_synthetic.sh (synthetic) exactly:
same scripts, same order, same --source flag. Nothing here re-implements the
pipeline; it only describes it.
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Dict, List

HERE = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.dirname(HERE)
PIPELINE_DIR = os.path.join(REPO_ROOT, "ml_pipeline")
DATA_DIR = os.path.join(REPO_ROOT, "data")

REAL = "real"
SYNTHETIC = "synthetic"
SOURCES = (REAL, SYNTHETIC)

# The interpreter the stages run under. The repo-root venv is the only one that
# carries shap + xgboost + networkx + matplotlib; aml-dashboard/backend/.venv
# does NOT, and pointing at it fails at stage 03. Overridable for debugging.
DEFAULT_PYTHON = os.environ.get(
    "AML_VIZ_PYTHON", os.path.join(REPO_ROOT, ".venv", "bin", "python")
)

# Every module a stage subprocess needs to import somewhere in the run.
REQUIRED_MODULES = (
    "pandas",
    "numpy",
    "sklearn",
    "scipy",
    "shap",
    "matplotlib",
    "xgboost",
    "networkx",
)

# Feature columns that only exist on the synthetic side, because they need a
# real time axis or counterparty edges. This asymmetry is the Tier A/Tier B
# argument, so the UI highlights them.
TIER_B_ONLY_FEATURES = (
    "active_days",
    "txn_per_active_day",
    "max_txn_1h",
    "sweep_latency_hr",
    "n_senders",
    "n_recipients",
    "pagerank",
    "betweenness",
    "fan_in_out_ratio",
)


@dataclass(frozen=True)
class Stage:
    id: str
    script: str
    label: str
    subtitle: str
    # artifacts written per source, in the order the UI should mention them
    artifacts: Dict[str, List[str]]
    # stage ids that must have completed first, per source
    depends_on: Dict[str, List[str]] = field(default_factory=dict)
    # rough seconds, per source — used only for the progress hint in the UI
    est_seconds: Dict[str, int] = field(default_factory=dict)

    def command(self, python: str, source: str) -> List[str]:
        return [python, self.script, "--source", source]


STAGES: List[Stage] = [
    Stage(
        id="00",
        script="00_eda_quality.py",
        label="Quality gate",
        subtitle="What is actually in the file, and what it forbids us from doing",
        artifacts={
            REAL: ["data_quality_report.md"],
            SYNTHETIC: ["data_quality_report_synthetic.md"],
        },
        depends_on={REAL: [], SYNTHETIC: []},
        est_seconds={REAL: 1, SYNTHETIC: 1},
    ),
    Stage(
        id="01",
        script="01_features.py",
        label="Features",
        subtitle="Transactions collapsed to one row per account",
        artifacts={
            REAL: ["account_features.csv"],
            SYNTHETIC: ["account_features_synthetic.csv"],
        },
        depends_on={REAL: [], SYNTHETIC: []},
        est_seconds={REAL: 1, SYNTHETIC: 2},
    ),
    Stage(
        id="02",
        script="02_score.py",
        label="Score",
        subtitle="Typology rules fused with an anomaly model into 0-100",
        artifacts={
            REAL: ["account_scores.csv", "rule_contributions.csv"],
            SYNTHETIC: [
                "account_scores_synthetic.csv",
                "rule_contributions_synthetic.csv",
            ],
        },
        depends_on={REAL: ["01"], SYNTHETIC: ["01"]},
        est_seconds={REAL: 2, SYNTHETIC: 4},
    ),
    Stage(
        id="03",
        script="03_explain.py",
        label="Explain",
        subtitle="SHAP attribution — why this account, in words",
        artifacts={
            REAL: ["explanations.csv", "shap_feature_importance.csv"],
            SYNTHETIC: [
                "explanations_synthetic.csv",
                "shap_feature_importance_synthetic.csv",
            ],
        },
        # real reads 02's rule_contributions + 01's features; the synthetic path
        # rebuilds features from the raw CSV in-process, so it needs no artifacts
        depends_on={REAL: ["01", "02"], SYNTHETIC: []},
        est_seconds={REAL: 5, SYNTHETIC: 4},
    ),
    Stage(
        id="04",
        script="04_validate.py",
        label="Validate",
        subtitle="Does the score survive contact with known answers?",
        artifacts={
            REAL: ["validation_report.md"],
            SYNTHETIC: ["validation_report_synthetic.md"],
        },
        # recomputes everything in-process from the raw CSV, so it needs nothing
        depends_on={REAL: [], SYNTHETIC: []},
        est_seconds={REAL: 4, SYNTHETIC: 5},
    ),
    Stage(
        id="05",
        script="05_report.py",
        label="Report",
        subtitle="The alert queue a human would actually receive",
        artifacts={
            REAL: ["flagged_mule_accounts.csv"],
            SYNTHETIC: ["flagged_mule_accounts_synthetic.csv"],
        },
        depends_on={REAL: ["02", "03"], SYNTHETIC: ["02", "03"]},
        est_seconds={REAL: 1, SYNTHETIC: 1},
    ),
    Stage(
        id="06",
        script="06_chart.py",
        label="Chart",
        subtitle="The pipeline's own rendering of the result",
        artifacts={REAL: ["risk_ranking.png"], SYNTHETIC: ["roc_pr_synthetic.png"]},
        depends_on={REAL: ["05"], SYNTHETIC: ["02"]},
        est_seconds={REAL: 1, SYNTHETIC: 2},
    ),
]

STAGES_BY_ID: Dict[str, Stage] = {s.id: s for s in STAGES}
STAGE_IDS: List[str] = [s.id for s in STAGES]

# Every filename any stage can produce — the image route allowlists against this.
ALL_ARTIFACTS = {
    name for stage in STAGES for names in stage.artifacts.values() for name in names
}


def source_meta() -> Dict[str, Dict[str, object]]:
    """Static descriptors for the two columns, shown before anything has run."""
    return {
        REAL: {
            "key": REAL,
            "label": "Real",
            "tier": "Tier A",
            "dataset": "data/mule_sample_data.csv",
            "blurb": "Finacle-style extract. Unlabeled, single timestamp, no counterparty.",
            "approach": "typology rules ⊕ Isolation Forest",
        },
        SYNTHETIC: {
            "key": SYNTHETIC,
            "label": "Synthetic",
            "tier": "Tier B",
            "dataset": "data/synthetic_scenario.csv",
            "blurb": "Jury-approved scenario set. Labeled, real time spread, counterparty edges.",
            "approach": "rules ⊕ Isolation Forest ⊕ supervised XGBoost",
        },
    }


def as_json() -> Dict[str, object]:
    return {
        "sources": source_meta(),
        "tier_b_only_features": list(TIER_B_ONLY_FEATURES),
        "stages": [
            {
                "id": s.id,
                "script": s.script,
                "label": s.label,
                "subtitle": s.subtitle,
                "artifacts": s.artifacts,
                "depends_on": s.depends_on,
                "est_seconds": s.est_seconds,
            }
            for s in STAGES
        ],
    }
