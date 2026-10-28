# ML Pipeline Visualizer

A standalone web app that runs `ml_pipeline/` **live**, one stage at a time, with
the real dataset and the synthetic dataset side by side. Click a button, the
stage actually executes as a subprocess for both sources at once, its stdout
streams into a log pane, and both columns fill with what that stage produced.

Nothing is pre-recorded. There is no cached fallback — a stage that fails, fails
on screen.

The `aml-dashboard/` workstation is untouched by this; the two apps share only
the `ml_pipeline/` scripts and the `data/` files.

## Run it

From the repo root:

```bash
./.venv/bin/python -m uvicorn ml_viz.server:app --port 8100
```

Open <http://localhost:8100>. That is the whole setup — no npm, no build step.

Add `--reload --reload-dir ml_viz` while editing.

**The interpreter matters.** Stages run under the repo-root `.venv`, the only one
carrying `shap`, `xgboost`, `networkx` and `matplotlib`. `aml-dashboard/backend/.venv`
lacks all four and stage 01 (synthetic) dies on `networkx`. Override with
`AML_VIZ_PYTHON=/path/to/python` if your venv lives elsewhere.

**Check the light before you present.** The chip in the top-right runs a preflight:
interpreter, the eight required modules, and the three data files. Hover it for
the per-check detail. Green means the demo will run.

## Controls

| | |
|---|---|
| **Run stage NN** | executes that stage for real + synthetic concurrently |
| **Run all remaining** | fast-forwards to the end (~12s for all seven) |
| **Both / Real / Synthetic** | which columns are on screen. Display only — both datasets always run, so you can switch sides mid-demo without re-running anything. Remembered across reloads. |
| `Space` / `→` | advance one stage — works from a presentation clicker |
| `←` | go back a stage (view only; does not re-run) |
| stage chips | jump to any stage already run |
| **Show log** | the raw stdout/stderr of both subprocesses, tagged by source |
| **New run** | fresh sandbox, everything back to pending |
| **Light / Dark** | dark by default; light reads better on some projectors |

## What each stage shows

| | Real — Tier A | Synthetic — Tier B |
|---|---|---|
| **00 Quality gate** | 2,000 txn / 19 accounts. Time axis ✗, counterparty ✗, labels ✗ | 9,481 txn / 330 accounts. All three ✓ |
| **01 Features** | 19 feature columns | 28 columns — the extra 9 highlighted |
| **02 Score** | rules ⊕ Isolation Forest, 14 of 19 flagged | + supervised XGBoost, 66 of 330 flagged |
| **03 Explain** | SHAP over the anomaly score | SHAP over the mule/not-mule decision |
| **04 Validate** | planted-account separation, Kendall τ 0.837 | ROC 0.996 · PR 0.982 · confusion matrix |
| **05 Report** | the alert queue, unverifiable | the same queue, scored against truth |
| **06 Chart** | `risk_ranking.png` | `roc_pr_synthetic.png` |

## Suggested demo narration

1. **Stage 00 — the whole argument.** Two quality gates side by side. The real
   file has no time axis, no counterparty column, no labels; the synthetic one
   has all three. *"This is why there are two tiers. You cannot XGBoost your way
   out of 19 unlabeled accounts."* Point at the concentration callout: one
   account holds 85% of the transactions.
2. **Stage 01.** Nine highlighted columns on the right. *"Timestamps and edges
   are what buy you velocity and graph centrality. The left column cannot have
   them — not because we didn't build them, because the data forbids it."*
3. **Stage 02.** The fusion formula reads its weights live from `common.py`.
   Then the number that matters: **14 of 19 flagged, and nobody can say how many
   are real.** *"That is reviewer backpressure. Detection is not the bottleneck."*
4. **Stage 04.** ROC 0.996 on the right — then read the amber caveat out loud
   before anyone else does. *"Known generative process. This is capability, not
   production performance."* On the left, the honest alternative when you have
   no labels: plant known accounts and check the cutoff lands between them.
5. **Stage 05.** The alert queue a human actually receives. Right column shows
   61 caught, 5 wasted reviews, 4 missed. Left column shows no such column,
   because there is no truth to score against.

If someone asks whether it is really running: open the log, and note the
transaction hashes and the `/var/folders/.../aml-viz-<run-id>/` paths scrolling
past. Or point out that stage 03 visibly takes ~3s while stage 05 is instant.

## How it works

```
ml_viz/
  stages.py     the 7-stage manifest — scripts, artifacts, dependencies
  runner.py     async subprocess driver + SSE event bus
  readers.py    artifact CSV/MD -> UI JSON
  server.py     FastAPI routes + static mount
  static/       index.html · app.js · panels.js · charts.js · style.css
```

Each stage is spawned exactly as `run_all.sh` spawns it —
`python 0N_x.py --source {real|synthetic}`, cwd `ml_pipeline/` — with
`AML_PIPELINE_OUT` pointed at a per-run temp directory. Real and synthetic never
write the same filename (the synthetic side is suffixed), so the two run
concurrently in one output dir.

Subprocesses rather than imports, deliberately: stage filenames start with digits
so they are not importable by name, every stage binds `OUT` at import time, and
`04_validate.py` mutates `02_score.RANDOM_STATE` globally — which would poison a
long-lived server process.

Runs live in memory and in a temp dir. Nothing is persisted; restart clears them.

### The one change to `ml_pipeline/`

`common.py` line 20:

```python
OUT = os.environ.get("AML_PIPELINE_OUT") or os.path.join(HERE, "output")
```

Unset, the behaviour is exactly as before, so `run_all.sh` and `run_synthetic.sh`
are unaffected and `ml_pipeline/output/` stays git-clean through any number of
demo runs.

### API

| Method | Path | |
|---|---|---|
| GET | `/api/preflight` | interpreter, module and data-file checks |
| GET | `/api/stages` | the manifest |
| POST | `/api/run` | new run → `{run_id, out_dir}` |
| POST | `/api/run/{id}/step?stage=NN` | run a stage (omit `stage` for the next one) |
| GET | `/api/run/{id}/events` | SSE: `log` · `status` · `stage_done` |
| GET | `/api/run/{id}/stage/{NN}` | parsed artifacts, both sources |
| GET | `/api/run/{id}/image/{file}` | the PNGs |

Swagger at `/api/docs`.

## Verifying it is the real pipeline

Run all seven stages, then diff the sandbox against the committed baseline:

```bash
diff -r --exclude=.DS_Store "$OUT_DIR" ml_pipeline/output
```

Seeds are fixed throughout (`RANDOM_STATE=42`), so all 20 artifacts — including
both PNGs — come out **byte-identical**. Verified on 2026-08-09.

`git status` stays clean after a run: nothing is written to `ml_pipeline/output/`
or `data/`.

## Known limits

- Stage 01 (synthetic) prints all 330 account IDs, so the log is noisy there.
  That is the pipeline's own stdout, left unfiltered on purpose.
- Runs are in-memory: a server restart mid-demo loses the current run. Just
  click **Run all remaining** again — it takes about twelve seconds.
- Per-stage timeout is 180s (`runner.STAGE_TIMEOUT_S`). Nothing comes close.
- No auth. Bind to localhost.
