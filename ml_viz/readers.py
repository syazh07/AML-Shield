"""Turn a stage's artifacts into UI-ready JSON.

Read-only: nothing here recomputes the pipeline. Where a number is displayed
next to a formula (stage 02), the constant is read from ml_pipeline/common.py
so the slide can never drift from the code.

Row-heavy tables are capped — the synthetic side has 330 accounts and only the
head of the ranking is legible from across a room anyway.
"""
from __future__ import annotations

import importlib.util
import os
import re
from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd

from . import stages as manifest
from .stages import REAL, SOURCES, SYNTHETIC

TOP_N = 25
HIST_BINS = 20


# --- ml_pipeline/common.py, loaded by path (same trick the dashboard uses) ----
def _load_common():
    path = os.path.join(manifest.PIPELINE_DIR, "common.py")
    spec = importlib.util.spec_from_file_location("ml_pipeline_common", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


_common = _load_common()
_raw_cache: Dict[str, pd.DataFrame] = {}


def _raw(source: str) -> pd.DataFrame:
    """The input dataset for a source. Cached — it never changes during a demo."""
    if source not in _raw_cache:
        _raw_cache[source] = _common.load(source)
    return _raw_cache[source]


def _short(acid: Any) -> str:
    return str(acid)[:6]


def _read_csv(out_dir: str, name: str) -> Optional[pd.DataFrame]:
    path = os.path.join(out_dir, name)
    return pd.read_csv(path) if os.path.exists(path) else None


def _read_text(out_dir: str, name: str) -> Optional[str]:
    path = os.path.join(out_dir, name)
    if not os.path.exists(path):
        return None
    with open(path, "r", encoding="utf-8") as fh:
        return fh.read()


def _num(value: Any) -> Any:
    """JSON-safe scalar (NaN/inf are not valid JSON)."""
    if value is None:
        return None
    if isinstance(value, (np.integer,)):
        return int(value)
    if isinstance(value, (np.floating, float)):
        f = float(value)
        return None if not np.isfinite(f) else round(f, 4)
    if isinstance(value, (np.bool_, bool)):
        return bool(value)
    return value


def _records(df: pd.DataFrame) -> List[Dict[str, Any]]:
    return [{k: _num(v) for k, v in row.items()} for row in df.to_dict("records")]


def _histogram(series: pd.Series, lo: float = 0.0, hi: float = 100.0) -> Dict[str, Any]:
    counts, edges = np.histogram(series.dropna(), bins=HIST_BINS, range=(lo, hi))
    return {
        "bins": [
            {"x0": round(float(edges[i]), 2), "x1": round(float(edges[i + 1]), 2),
             "count": int(counts[i])}
            for i in range(len(counts))
        ],
        "max": int(counts.max()) if len(counts) else 0,
    }


def _curve(xs: np.ndarray, ys: np.ndarray, points: int = 120) -> List[Dict[str, float]]:
    """Downsample a metric curve to something an SVG path can carry."""
    if len(xs) <= points:
        idx = range(len(xs))
    else:
        idx = np.unique(np.linspace(0, len(xs) - 1, points).astype(int))
    return [{"x": round(float(xs[i]), 4), "y": round(float(ys[i]), 4)} for i in idx]


# --- stage 00: quality gate ---------------------------------------------------
def read_00(out_dir: str, source: str) -> Dict[str, Any]:
    df = _raw(source)
    report = _read_text(
        out_dir,
        "data_quality_report.md" if source == REAL
        else "data_quality_report_synthetic.md",
    )

    has_time = bool(_common.has_time_axis(df))
    has_party = bool(_common.has_counterparty(df))
    has_labels = "is_mule" in df.columns and df["is_mule"].notna().any()

    # constant columns carry no information and get dropped downstream
    dead = [
        {"column": c, "value": str(df[c].dropna().iloc[0])[:40]}
        for c in df.columns
        if df[c].nunique(dropna=True) == 1 and c not in ("source",)
    ]

    direction = (
        df["PART_TRAN_TYPE"].value_counts().to_dict()
        if "PART_TRAN_TYPE" in df.columns else {}
    )
    channels = (
        df["channel"].value_counts().head(6).to_dict() if "channel" in df.columns else {}
    )
    amt = df["TRAN_AMT"].dropna()

    payload: Dict[str, Any] = {
        "dataset": os.path.basename(
            _common.RAW_CSV if source == REAL else _common.SYN_CSV
        ),
        "counts": {
            "transactions": int(len(df)),
            "accounts": int(df["ACID"].nunique()),
            "customers": int(df["CIF_ID"].nunique()) if "CIF_ID" in df.columns else None,
        },
        # the capability matrix — this is the argument for two tiers
        "capabilities": [
            {
                "name": "Time axis",
                "ok": has_time,
                "detail": f"{int(df['TRAN_DATE'].nunique())} distinct timestamps"
                if has_time else "one frozen timestamp",
                "unlocks": "velocity, burst, sweep-latency features",
            },
            {
                "name": "Counterparty edges",
                "ok": has_party,
                "detail": "BENEFICIARY_ACID present" if has_party
                else "no beneficiary column",
                "unlocks": "PageRank, betweenness, fan-in/fan-out",
            },
            {
                "name": "Ground-truth labels",
                "ok": bool(has_labels),
                "detail": "is_mule present" if has_labels else "unlabeled",
                "unlocks": "supervised training, ROC/PR, precision & recall",
            },
        ],
        "dead_columns": dead,
        "direction": {str(k): int(v) for k, v in direction.items()},
        "channels": {str(k): int(v) for k, v in channels.items()},
        "amount": {
            "min": _num(amt.min()),
            "median": _num(amt.median()),
            "mean": _num(amt.mean()),
            "max": _num(amt.max()),
        },
        "report_md": report,
    }

    if has_labels:
        labels = df.groupby("ACID")["is_mule"].max()
        payload["labels"] = {
            "mules": int((labels == 1).sum()),
            "normals": int((labels == 0).sum()),
        }
    if "typology" in df.columns:
        typ = df.groupby("ACID")["typology"].first().value_counts()
        payload["typologies"] = {str(k): int(v) for k, v in typ.items()}
    if source == REAL:
        busiest = df["ACID"].value_counts()
        payload["concentration"] = {
            "top_account": _short(busiest.index[0]),
            "txns": int(busiest.iloc[0]),
            "share": round(float(busiest.iloc[0] / len(df)), 4),
        }
    return payload


# --- stage 01: features -------------------------------------------------------
def read_01(out_dir: str, source: str) -> Dict[str, Any]:
    name = "account_features.csv" if source == REAL else "account_features_synthetic.csv"
    feat = _read_csv(out_dir, name)
    if feat is None:
        return {"missing": name}

    # is_mule/typology are the ground truth carried alongside, not model inputs
    # (supervised.py excludes is_mule). Counting them would overstate the feature
    # count and contradict "28 features" in the validation report.
    labels = [c for c in ("is_mule", "typology") if c in feat.columns]
    skip = {"ACID", "source", *labels}
    columns = []
    for col in feat.columns:
        if col in skip:
            continue
        entry: Dict[str, Any] = {
            "name": col,
            "tier_b_only": col in manifest.TIER_B_ONLY_FEATURES,
        }
        if pd.api.types.is_numeric_dtype(feat[col]):
            entry.update(
                min=_num(feat[col].min()),
                mean=_num(feat[col].mean()),
                max=_num(feat[col].max()),
            )
        columns.append(entry)

    preview_cols = [c for c in feat.columns if c not in skip][:8]
    preview = feat[["ACID"] + preview_cols].head(8).copy()
    preview["ACID"] = preview["ACID"].map(_short)

    return {
        "rows": int(len(feat)),
        "n_columns": len(columns),
        "n_tier_b_only": sum(1 for c in columns if c["tier_b_only"]),
        "label_columns": labels,
        "columns": columns,
        "preview_columns": ["ACID"] + preview_cols,
        "preview": _records(preview),
    }


# --- stage 02: score ----------------------------------------------------------
def read_02(out_dir: str, source: str) -> Dict[str, Any]:
    suffix = "" if source == REAL else "_synthetic"
    scores = _read_csv(out_dir, f"account_scores{suffix}.csv")
    contrib = _read_csv(out_dir, f"rule_contributions{suffix}.csv")
    if scores is None:
        return {"missing": f"account_scores{suffix}.csv"}

    threshold = float(_common.FLAG_THRESHOLD)
    rule_cols = list(_common.RULE_CAPS.keys())

    top = scores.sort_values("composite_risk", ascending=False).head(TOP_N).copy()
    if contrib is not None:
        top = top.merge(contrib[["ACID"] + rule_cols], on="ACID", how="left")
    top.insert(0, "Account", top["ACID"].map(_short))
    top = top.drop(columns=["ACID"])

    firing = {}
    if contrib is not None:
        for col in rule_cols:
            firing[col] = {
                "accounts_firing": int((contrib[col] > 0).sum()),
                "mean_when_firing": _num(contrib.loc[contrib[col] > 0, col].mean()),
                "max": _num(contrib[col].max()),
                "cap": _num(_common.RULE_CAPS[col]),
            }

    payload: Dict[str, Any] = {
        "rows": int(len(scores)),
        "threshold": threshold,
        "flagged": int((scores["composite_risk"] >= threshold).sum()),
        "fusion": {
            "w_rule": _num(_common.W_RULE),
            "w_anom": _num(_common.W_ANOM),
            "has_supervised": "supervised_score" in scores.columns,
            # 02_score.py blends the supervised term into the composite only on
            # the labelled side; the weights above are the unsupervised anchor.
            "formula": "0.65 · rule ⊕ 0.35 · anomaly"
            + (" ⊕ supervised" if "supervised_score" in scores.columns else ""),
        },
        "rule_columns": rule_cols,
        "rule_firing": firing,
        "histogram": _histogram(scores["composite_risk"]),
        "top": _records(top),
        "top_columns": list(top.columns),
    }
    if "is_mule" in scores.columns:
        flagged = scores["composite_risk"] >= threshold
        payload["label_split"] = {
            "flagged_mules": int((flagged & (scores["is_mule"] == 1)).sum()),
            "flagged_normals": int((flagged & (scores["is_mule"] == 0)).sum()),
            "missed_mules": int((~flagged & (scores["is_mule"] == 1)).sum()),
        }
    return payload


# --- stage 03: explain --------------------------------------------------------
def read_03(out_dir: str, source: str) -> Dict[str, Any]:
    suffix = "" if source == REAL else "_synthetic"
    imp = _read_csv(out_dir, f"shap_feature_importance{suffix}.csv")
    expl = _read_csv(out_dir, f"explanations{suffix}.csv")
    if imp is None:
        return {"missing": f"shap_feature_importance{suffix}.csv"}

    imp = imp.sort_values("mean_abs_shap", ascending=False).head(12)

    # The two sides genuinely explain different models, so the tables differ.
    # Normalise to one shape and tell the UI what it is looking at.
    rows: List[Dict[str, Any]] = []
    if expl is not None:
        e = expl.copy()
        e["Account"] = e["ACID"].map(_short)
        if source == REAL:
            e = e.head(TOP_N)
            rows = _records(
                e[["Account", "reason", "top_anomaly_feature", "top_anomaly_shap"]]
                .rename(columns={
                    "top_anomaly_feature": "driver", "top_anomaly_shap": "shap"})
            )
        else:
            e = e.reindex(e["top_supervised_shap"].abs().sort_values(
                ascending=False).index).head(TOP_N)
            rows = _records(
                e[["Account", "is_mule", "top_supervised_feature", "top_supervised_shap"]]
                .rename(columns={
                    "top_supervised_feature": "driver", "top_supervised_shap": "shap"})
            )

    return {
        "model": "Isolation Forest — model-agnostic shap.Explainer"
        if source == REAL else "XGBoost — exact shap.TreeExplainer",
        "explains": "what makes this account unusual"
        if source == REAL else "what the model learned separates mules",
        "n_features": int(len(imp)),
        "importance": _records(imp),
        "rows": rows,
        "row_columns": ["Account", "reason", "driver", "shap"]
        if source == REAL else ["Account", "is_mule", "driver", "shap"],
        "schema_note": "Unlabeled data has no target to attribute to, so the real "
        "side explains the anomaly score and pairs it with the rule that fired."
        if source == REAL else
        "Labels let SHAP attribute directly to the mule/not-mule decision.",
    }


_METRIC_PATTERNS = (
    ("ROC-AUC", r"\*\*ROC-AUC:\s*([0-9.]+)\*\*"),
    ("PR-AUC", r"\*\*PR-AUC \(average precision\):\s*([0-9.]+)\*\*"),
    ("5-fold CV", r"5-fold CV ROC-AUC:\s*\*\*([0-9.]+ ± [0-9.]+)\*\*"),
    ("Precision", r"Precision \*\*([0-9.]+)\*\*"),
    ("Recall", r"Recall \*\*([0-9.]+)\*\*"),
    ("F1", r"F1 \*\*([0-9.]+)\*\*"),
    ("Kendall τ", r"Kendall's tau across 5 seeds:\s*\*\*([0-9.]+)\*\*"),
)


# --- stage 04: validate -------------------------------------------------------
def read_04(out_dir: str, source: str) -> Dict[str, Any]:
    name = "validation_report.md" if source == REAL else "validation_report_synthetic.md"
    report = _read_text(out_dir, name)
    if report is None:
        return {"missing": name}

    metrics = []
    for label, pattern in _METRIC_PATTERNS:
        match = re.search(pattern, report)
        if match:
            metrics.append({"label": label, "value": match.group(1)})

    payload: Dict[str, Any] = {
        "metrics": metrics,
        "verdict": "PASS" if "PASS" in report else None,
        "report_md": report,
        "caveat": None,
    }

    if source == REAL:
        # separation table: | name | type | rank | composite | flagged |
        seps = []
        for m in re.finditer(
            r"^\|\s*(MULE_\w+|NORMAL_\w+)\s*\|\s*(\w+)\s*\|\s*(\d+)\s*\|"
            r"\s*([0-9.]+)\s*\|\s*(YES|no)\s*\|",
            report, re.MULTILINE,
        ):
            seps.append({
                "account": m.group(1), "type": m.group(2), "rank": int(m.group(3)),
                "composite": float(m.group(4)), "flagged": m.group(5) == "YES",
            })
        payload["separation"] = seps
        payload["method"] = (
            "No labels exist, so validation plants two known mules and two known "
            "normals, rescores, and checks the cutoff lands between them."
        )
    else:
        payload["method"] = (
            "Labels exist, so this is measured the ordinary way: out-of-fold "
            "predictions, ROC/PR, and a confusion matrix at 0.5."
        )
        payload["caveat"] = (
            "Synthetic data has a known generative process. These numbers show "
            "capability, not production performance."
        )
        cm = re.search(
            r"\|\s*\*\*actual normal\*\*\s*\|\s*(\d+)\s*\|\s*(\d+)\s*\|\s*\n"
            r"\|\s*\*\*actual mule\*\*\s*\|\s*(\d+)\s*\|\s*(\d+)\s*\|",
            report,
        )
        if cm:
            payload["confusion"] = {
                "tn": int(cm.group(1)), "fp": int(cm.group(2)),
                "fn": int(cm.group(3)), "tp": int(cm.group(4)),
            }
        # curves drawn from the scores themselves, not lifted off the PNG
        scores = _read_csv(out_dir, "account_scores_synthetic.csv")
        if scores is not None and "supervised_score" in scores.columns:
            from sklearn.metrics import precision_recall_curve, roc_curve

            y = scores["is_mule"].astype(int).to_numpy()
            p = (scores["supervised_score"] / 100.0).to_numpy()
            fpr, tpr, _ = roc_curve(y, p)
            prec, rec, _ = precision_recall_curve(y, p)
            payload["roc"] = _curve(fpr, tpr)
            payload["pr"] = _curve(rec, prec)
            payload["positive_rate"] = round(float(y.mean()), 4)
    return payload


# --- stage 05: report ---------------------------------------------------------
def read_05(out_dir: str, source: str) -> Dict[str, Any]:
    name = ("flagged_mule_accounts.csv" if source == REAL
            else "flagged_mule_accounts_synthetic.csv")
    rep = _read_csv(out_dir, name)
    if rep is None:
        return {"missing": name}

    threshold = float(_common.FLAG_THRESHOLD)
    rep = rep.sort_values("Risk_Score", ascending=False)
    flagged = rep["Is_Flagged"].astype(str).str.lower() == "true"

    if source == REAL:
        cols = ["Account", "Risk_Score", "Is_Flagged", "Rule_Score",
                "Anomaly_Score", "Top_Anomaly_Feature", "Top_Reasons"]
    else:
        cols = ["Account", "Risk_Score", "Is_Flagged", "True_Mule", "Correct",
                "Rule_Score", "Anomaly_Score", "Supervised_Score",
                "Top_Supervised_Feature"]
    cols = [c for c in cols if c in rep.columns]

    payload: Dict[str, Any] = {
        "total": int(len(rep)),
        "flagged": int(flagged.sum()),
        "threshold": threshold,
        "columns": cols,
        "rows": _records(rep[cols].head(TOP_N)),
    }
    if "Correct" in rep.columns and "True_Mule" in rep.columns:
        truth = rep["True_Mule"].astype(int) == 1
        payload["outcome"] = {
            "true_positive": int((flagged & truth).sum()),
            "false_positive": int((flagged & ~truth).sum()),
            "false_negative": int((~flagged & truth).sum()),
            "true_negative": int((~flagged & ~truth).sum()),
        }
    else:
        payload["outcome_note"] = (
            "No labels, so there is no true/false column to show — this queue is "
            "exactly what a reviewer would receive, unverified."
        )
    return payload


# --- stage 06: chart ----------------------------------------------------------
_CAPTIONS = {
    "risk_ranking.png": "Composite risk per account, cutoff at 60",
    "roc_pr_synthetic.png": "ROC and Precision-Recall for the supervised model",
}


def read_06(out_dir: str, source: str) -> Dict[str, Any]:
    stage = manifest.STAGES_BY_ID["06"]
    images = []
    for name in stage.artifacts[source]:
        if os.path.exists(os.path.join(out_dir, name)):
            images.append({"filename": name, "caption": _CAPTIONS.get(name, name)})
    return {
        "images": images,
        "note": "The pipeline's own matplotlib output — the same PNG that lands "
                "in ml_pipeline/output on a headless run.",
    }


_READERS = {
    "00": read_00, "01": read_01, "02": read_02, "03": read_03,
    "04": read_04, "05": read_05, "06": read_06,
}


def read_stage(out_dir: str, stage_id: str, state: Dict[str, Any]) -> Dict[str, Any]:
    """Parsed artifacts for one stage, both sources.

    A source that has not run (or failed) reports `available: false` rather than
    inventing data — a failed stage stays visibly failed.
    """
    reader = _READERS[stage_id]
    out: Dict[str, Any] = {"stage": stage_id, "sources": {}}
    for source in SOURCES:
        source_state = state["sources"][source]
        if source_state["status"] != "done":
            out["sources"][source] = {
                "available": False,
                "status": source_state["status"],
                "error": source_state.get("error"),
            }
            continue
        try:
            payload = reader(out_dir, source)
            payload.update(available=True, status="done",
                           duration_s=source_state.get("duration_s"))
        except Exception as exc:  # a parse failure must not blank the whole page
            payload = {"available": False, "status": "parse_error", "error": str(exc)}
        out["sources"][source] = payload
    return out
