# AML Shield — Data Flow & Architecture

How data moves through the system, what each ML‑pipeline file does, and where the
backend gets its data. The system is **two decoupled halves joined by two thin
seams**: an offline analytics pipeline (batch) and a live web app (FastAPI +
React). Nothing streams between them at runtime — they share *code* and a *data
contract*, not a database.

---

## 1. Big picture

```
        OFFLINE (batch, analyst laptop)               ONLINE (FastAPI + React, live)
  ┌───────────────────────────────────┐      ┌────────────────────────────────────────┐
  │  data/mule_sample_data.csv (REAL)  │      │  React workstation (aml-dashboard/src)   │
  │  data/synthetic_scenario.csv (SYN) │      │        │  fetch /api/v1/...               │
  │            │                       │      │        ▼                                 │
  │   ml_pipeline/00..06 + synth       │      │  FastAPI routers (app/api/v1/*)          │
  │            │  writes               │      │        │                                 │
  │            ▼                       │      │        ▼                                 │
  │  ml_pipeline/output/*.csv,*.md,*.png│     │  Services (cases, str, ml, copilot...)   │
  │  (reports for the JURY / deck)     │      │        │            │                    │
  └───────────────────────────────────┘      │        ▼            ▼                    │
                │                             │  SQLite Store   MLPipelineScoringService  │
        SEAM 1  │ imports common.py           │  (runtime DB)        │                    │
        (RULE_CAPS, W_RULE/W_ANOM, load_raw)  │                      │ SEAM 1             │
                └─────────────────────────────┼──────────────────────┘                    │
                                              │  SEAM 2 = /ml/score schema contract        │
                                              └────────────────────────────────────────┘
```

> **Key fact:** the backend **does not read the pipeline's CSV outputs**. The
> `output/*.csv` files are batch deliverables for the jury/deck. At runtime the
> backend re‑uses the pipeline's *code* (`common.py`) and re‑fits its own
> Isolation Forest in memory at startup.

---

## 2. The offline ML pipeline (`ml_pipeline/`)

Each stage reads the previous stage's file(s) and writes its own. Default is
`--source real`; `--source synthetic` runs the Tier‑B path on the labeled
synthetic scenario. Real outputs are unsuffixed; synthetic outputs are
`*_synthetic.*`.

| File | Role | Reads → Writes |
|---|---|---|
| **`common.py`** | Shared foundation: paths, `RULE_CAPS`, fusion weights `W_RULE`/`W_ANOM`, `FLAG_THRESHOLD`, loaders. `load_raw()` (real‑only, unchanged), `load_synthetic()`, `load(source)`, `has_time_axis()`, `has_counterparty()`. | — |
| **`00_eda_quality.py`** | Data‑quality gate. Real: documents the file's limits (constant date, no counterparty…). Synthetic: asserts the Tier‑B inputs (timestamps, edges, labels) are present. | data → `data_quality_report[_synthetic].md` |
| **`01_features.py`** | Aggregates transactions → one row per account. Base count/ratio features always; temporal + graph (networkx) features **only when the data supports them** (synthetic). | data → `account_features[_synthetic].csv` |
| **`02_score.py`** | Scoring. Anchor = noisy‑OR rules ⊕ Isolation Forest → 0–100 composite. Synthetic also fuses an **XGBoost** term (out‑of‑fold). | features → `account_scores[_synthetic].csv`, `rule_contributions[_synthetic].csv` |
| **`supervised.py`** | Shared XGBoost helper (feature selection, model config, out‑of‑fold probabilities, full fit for SHAP). Used by 02/03/04 so they stay consistent. Synthetic‑only. | — |
| **`03_explain.py`** | Explainability. Real: rule reason strings + SHAP on the Isolation Forest. Synthetic: **TreeExplainer SHAP on XGBoost**. | features/contrib → `explanations[_synthetic].csv`, `shap_feature_importance[_synthetic].csv` |
| **`04_validate.py`** | Validation. Real: planted mule‑vs‑normal separation + Isolation‑Forest seed stability. Synthetic: **ROC‑AUC / PR‑AUC / precision‑recall / CV** + real‑anchor sanity check. | → `validation_report[_synthetic].md` |
| **`05_report.py`** | Final deliverable CSV (score + reasons + flag; synthetic adds correctness vs ground truth). | scores+expl → `flagged_mule_accounts[_synthetic].csv` |
| **`06_chart.py`** | Charts for the deck. Real: risk‑ranking bar. Synthetic: **ROC + PR curves**. | → `risk_ranking.png`, `roc_pr_synthetic.png` |
| **`synth/generate.py`** | Generates the labeled synthetic scenario (timestamps + counterparty edges + `is_mule`, incl. a coin‑flip "ambiguous" group so ROC‑AUC stays < 1). | → `data/synthetic_scenario.csv`, `data/synthetic_accounts.csv` |
| **`run_all.sh` / `run_synthetic.sh`** | Orchestrate the real (`00→06`) and synthetic (`generate → 06 --source synthetic`) runs. | — |

### Pipeline stage chain

```
        (real)                                   (synthetic)
raw CSV                                  synth/generate.py → synthetic_scenario.csv
  │                                                │
  ▼                                                ▼
00 quality → 01 features → 02 score → 03 explain → 04 validate → 05 report → 06 chart
                 │             │            │            │            │
          account_features  account_scores  explanations validation  flagged_mule_accounts
```

---

## 3. The datasets

| Dataset | What it is | Used by |
|---|---|---|
| **`data/mule_sample_data.csv`** | The real IOB sample: 2000 txns, **19 accounts**, no labels, no real timestamps, no counterparty. The *reality anchor*. | Real pipeline **and** the live backend model |
| **`data/synthetic_scenario.csv`** + **`synthetic_accounts.csv`** | Jury‑approved augmentation: 330 accounts *with* labels, timestamps, and counterparty edges. Separate file, never mixed into the real path. | Synthetic pipeline only (**not** the backend) |

> Rationale and the hybrid decision are in [WHITEPAPER.md](WHITEPAPER.md) /
> [THESIS.md](THESIS.md): the real 19 accounts stay the unsupervised anchor;
> synthetic drives the supervised + graph + temporal capability demo, with
> metrics reported as *capability, not production performance*.

---

## 4. Where the backend gets its data (3 distinct sources)

**1. The ML model (scores + risk signals) — `app/services/ml_pipeline_service.py`**
At startup `MLPipelineScoringService` `importlib`‑loads `ml_pipeline/common.py`,
reads `RULE_CAPS` / `W_RULE` / `W_ANOM`, calls `load_raw()` for the real 2000
txns, and **fits an Isolation Forest in memory**. It then scores case bundles live
via `score_account(bundle)` and single transactions via `score_transaction()`.
This is **Seam 1** — it uses the pipeline's *code*, not its CSVs, and not the
synthetic data.

**2. Case / investigation content — seed + generator + Store**
- `app/data/seed.py` — the hand‑authored showcase case `IOB-2024-MU-4471`
  (profile, timeline, 6‑node graph, risk signals, STR narrative, audit log).
- `app/data/investigation_gen.py` — deterministically generates full bundles for
  *every other* case (reusing the same 5 timestamps / 6‑node topology so the d3
  viz stays stable across cases and restarts).
- `app/data/seeding.py` — on first boot, seeds those cases into the Store,
  scoring each through the ML service so the score + signal breakdown trace to the
  real model.

**3. The runtime database — `app/persistence.py` (`Store`, SQLite)**
Persists cases, notes, the append‑only audit chain, investigation bundles, STR
drafts, notifications, and chat. This is what survives across requests/restarts
(`reset_db.py` / `Store.wipe()` returns to a clean slate). The frontend's live
reads/writes go here.

### Runtime request flow

```
React fetch('/api/v1/...')  →  Vite proxy  →  FastAPI router (app/api/v1/*)
      →  service (case_service / str_service / ml / copilot / notification)
      →  Store (persistent data)  and/or  MLPipelineScoringService (live scoring)
      →  JSON response (camelCase via Pydantic schema aliases)
```

---

## 5. What is "synced" vs independent

**Synced — the two seams the backend depends on:**
1. **`ml_pipeline/common.py`** — rule caps, fusion weights, and `load_raw()`.
   Change these and the backend's live scoring changes too.
2. **The `/ml/score` schema** — `TransactionFeatures` → `CaseScoreResult` +
   `SignalContribution`, formalized as the `ScoringModel` Protocol
   (`app/services/scoring.py`). Any model that satisfies it is a drop‑in; nothing
   else in the backend reaches past these members.

**NOT synced — independent:**
- Pipeline `output/*.csv` — batch reports; the backend never reads them.
- The synthetic dataset & Tier‑B models (XGBoost / graph / temporal) — pipeline
  only. The backend still loads **real** data via `load_raw()`, so the synthetic
  work has **zero runtime effect on the backend**.
- Workstation graph/timeline visuals — authored/generated seed data, not derived
  from either dataset (the real file can't supply edges or a time axis).

---

## 6. The connector contract (`ScoringModel`)

The backend is a **model‑agnostic connector**: it never trains or hard‑codes a
detector, it only depends on this interface (`app/services/scoring.py`).

```python
class ScoringModel(Protocol):
    MODEL_VERSION: str
    MODEL_TYPE: str
    IS_PLACEHOLDER: bool
    async def score_transaction(self, features: TransactionFeatures) -> CaseScoreResult: ...
    def score_account(self, bundle: dict) -> dict: ...
```

`MLPipelineScoringService` (the current hybrid) structurally implements it. Swap
it for a supervised XGBoost service, a graph model, or an external scoring API
without touching endpoints, schemas, or the workstation — that is the "model is a
commodity plug behind the reviewer workstation" thesis, made literal.

Consumers of the seam: `app/core/state.py`, `app/api/v1/ml.py`,
`app/api/v1/health.py`, `app/data/seeding.py`, `app/services/case_service.py`.

---

## 7. Two data planes: model vs narrative

A common question: *"the sample CSV has `ACID`, `ACCT_OPN_DATE`, `balance`,
`customer_age` — why doesn't the profile card use them?"* The answer is that the
system has **two separate data planes**, and only one of them is fed by the CSV.

- **Model plane** — real CSV numeric fields → detection score + risk signals.
- **Narrative plane** — fabricated profile / graph / timeline → what the analyst
  reads on screen.

### The model plane *does* use the CSV
Every field in the extract that carries signal is consumed by `ml_pipeline`:

| CSV field | Used how |
|---|---|
| `ACID` | grouping key — one feature row per account |
| `ACCT_OPN_DATE` | → `account_age_days`, tenure, new‑account‑burst (`01_features.py`) |
| `balance` | feature in the transaction‑level Isolation Forest (`02_score.py`) |
| `TRAN_AMT` | amount profile, structuring band, pass‑through ratios |
| `PART_TRAN_TYPE` | credit/debit direction — the strongest usable signal |
| `channel`, `LIEN_AMT` | UPI share, lien‑to‑turnover ratio |
| `customer_age` | **profiled but dropped** — it's `30` for ~85% of rows (imputed), so it's noise |

So the detector is not ignoring the real data — it uses everything trustworthy.

### The narrative plane is fabricated (demo scaffolding)
The Sidebar profile card (`type`, `opened`, `dormant`, `branch`, `kyc`, `mobile`,
`pan`, `balanceBefore`/`balancePeak`/`balanceCurrent`) is **not** read from the
CSV, for three independent reasons:

1. **Most fields aren't in the file at all** — `branch`, `mobile`, `PAN`, `KYC`,
   account `type` are simply not columns. Nothing to read.
2. **The demo cases aren't the CSV's accounts** — the seeded cases (`AC7823901`,
   the `IOB-2024-MU-*` ids) are a curated storyline; they do **not** map 1:1 to
   the 19 hashed ACIDs in the CSV. So even for a field that exists (opening date),
   there is no matching CSV row for case `AC7823901`.
3. **The fields that do exist are low quality** — `balance` "doesn't reconcile
   with amounts" (shuffled/synthetic), `customer_age` is mostly imputed,
   `LIEN_AMT` is a near‑constant injected value. Fine as coarse ML features; not
   trustworthy enough to render as a factual account statement.

These values come from `app/data/seed.py` (the hero case, hand‑authored) and
`app/data/investigation_gen.py` (all other cases, deterministically generated).
The masked `mobile`/`PAN` (`94XXXXXXX4`, `BXXXX1234X`) are intentionally fake.

> **For a jury:** if asked "is this PAN real / does this come from the data?", the
> honest answer is no — the profile/graph/timeline are a realistic **mock of the
> enrichment systems** a bank would join in. The real CSV proves the *model*
> works on genuine transaction data.

---

## 8. What this maps to in a real production system

The single pipe‑delimited CSV is a stand‑in for **one anonymized transaction
extract from a Core Banking System** (the `TRAN_*` / `ACID` / Finacle‑style
columns give it away). In production you never have "one CSV" — you have a set of
source systems, each keyed by `ACID` / `CIF_ID`:

| Source system | Provides |
|---|---|
| **Core Banking System (CBS)** | accounts, balances, opening date, dormancy flags, account type |
| **Transaction Monitoring (TM) engine** | the alerts that *start* a case |
| **CIF / KYC master** | identity: name, PAN, mobile, branch, KYC tier |
| **Payments / ledger** | beneficiary/counterparty legs → the money‑flow graph |
| **Device / session / channel logs** | device fingerprint, IP, geo (impossible‑travel) |
| **Case management history** | prior SARs/STRs, confirmed‑mule labels |

The profile card the analyst sees would, in prod, be **assembled by joining
CBS + CIF + device logs** on the account/customer id — not read from the
transaction feed.

### The backend, in production, is an enrichment + orchestration layer

```
TM engine fires an alert (ACID, rule, score)
        │
        ▼
Backend (orchestrator):
   ├─ join CIF/KYC master      → identity card (PAN, mobile, branch, KYC)
   ├─ join CBS account master  → type, open date, dormancy, balances
   ├─ pull txn history + ledger → timeline + counterparty graph
   ├─ call the detection MODEL  → score + explainable signals   ← the /ml/score seam
   └─ assemble one case bundle
        │
        ▼
Investigator workstation (React) — review, note, escalate, file STR
```

### How this project mocks that fabric

| Production component | This project's stand‑in |
|---|---|
| CBS / CIF / ledger joins (profile, timeline, graph) | `app/data/seed.py` + `app/data/investigation_gen.py` (invented, deterministic) |
| TM engine + detection model | `MLPipelineScoringService` — the **only** component wired to the real CSV |
| Case‑management database | `app/persistence.py` (`Store`, SQLite) |

So the real CSV proves the **model** works on genuine transaction data; the
profile/graph/timeline are a deliberate **mock of the enrichment systems**,
because those systems (and their PAN/branch/device data) aren't present in a
13‑column transaction extract.

**Path to "real" end‑to‑end:** replace `investigation_gen.py`'s random profile
with a CIF/CBS lookup service, and derive the graph from a real beneficiary
column — exactly the Tier‑B counterparty edge the synthetic dataset now
demonstrates (see §3 and [WHITEPAPER.md](WHITEPAPER.md)).

---

## 9. Field‑by‑field provenance (dashboard) — the jury cheat‑sheet

Every field the workstation shows, and where its value comes from. Use this to
answer "is this real or made up?" instantly.

### Provenance legend

| Tag | Meaning | Where |
|---|---|---|
| **CSV** | The real sample transaction fields | `data/mule_sample_data.csv` |
| **MODEL** | Computed by the detector, which is **fitted on the real CSV** | `MLPipelineScoringService` |
| **SEED** | Hand‑authored demo constants (showcase case + team + notifications) | `app/data/seed.py` |
| **GEN** | Deterministically generated per case id (stable across restarts) | `app/data/investigation_gen.py` |
| **RUNTIME** | Created during the session (typed notes, slider, actions, STR edits) | `Store` |
| **LLM** | Generated by OpenAI at runtime, grounded in the case | `copilot_service` / `str_service` |
| **SYNTHETIC** | The labeled synthetic dataset — **never shown in the dashboard** | pipeline only |

### ⚡ Quick answers for the jury

- **"Is the dashboard showing the CSV data?"** → No. The case list, profiles,
  timeline, and graph are **demo data** (SEED for the showcase case
  `IOB‑2024‑MU‑4471`; GEN for the other five). The CSV feeds only the **model**.
- **"So what on screen is from real data?"** → The **risk score and signal
  breakdown of the five non‑showcase cases** — produced by the model fitted on
  the real CSV. Everything else on screen is demo scaffolding.
- **"Where's the synthetic data in the app?"** → Nowhere. Synthetic lives only in
  `ml_pipeline` (supervised/graph/temporal demo). It has **zero** runtime effect
  on the backend or UI.
- **"Is this PAN / mobile / device hash real?"** → No — masked, invented values
  (`94XXXXXXX4`, `BXXXX1234X`, `sha256: 4c9e…b8f2`). Demo scaffolding.
- **"Why is the showcase case different?"** → `IOB‑2024‑MU‑4471` is 100%
  hand‑authored (even its score `91` is a literal) so the demo has one perfect,
  narrated case. The other five are model‑scored on generated behaviour.

### Case Pool (case list card)

| Field | Source | How |
|---|---|---|
| `id`, `account`, `type`, `flag`, `status`, `claimedBy`, `openedMin`, `strDeadlineHrs`, `urgent`, `closedReason` | **SEED** | Literals in `seed.CASES` (6 curated cases) |
| `score` | **SEED** for `…4471`; **MODEL** for the other 5 | Showcase keeps its literal `91`; others are overwritten by `ml.score_account(bundle)` at seed time (`seeding.py`) |

### Investigation — top bar

| Field | Source | How |
|---|---|---|
| account, risk badge (score), status badge, claimed‑by | **SEED / MODEL** | Same as Case Pool |
| STR status badge | **RUNTIME** | Starts `none`; changes via STR actions |

### Sidebar — account profile

`IOB‑2024‑MU‑4471` → **SEED** (`ACCOUNT_PROFILE`). All other cases → **GEN**.

| Field | Source | How |
|---|---|---|
| `account`, `type` | SEED/case | From the case record |
| `opened`, `dormant` | SEED / GEN | Showcase: authored strings. Others: `rng.randint` months |
| `branch`, `kyc` | SEED / GEN | Others: `rng.choice` from a small list |
| `mobile`, `pan` | SEED / GEN | **Masked fake** (`9XXXXXXX#`, `XXXX####X`) |
| `balanceBefore`, `balancePeak`, `balanceCurrent` | SEED / GEN | Others: random ₹ around `amount_in` |
| Non‑primary graph node clicked | derived | Frontend fills `—` placeholders (only the primary account has a full profile) |

### Investigation — timeline events

`…4471` → **SEED** (`TIMELINE`). Others → **GEN**.

| Field | Source | How |
|---|---|---|
| `t` (time) | SEED / GEN | Fixed 5‑event clock `_TIMES` (shared so the d3 viz stays stable) |
| `amt` | SEED / GEN | Others: `amount_in` from a fixed list; outs = `amount_in × ratio_target × split` |
| `party` | SEED / GEN | Others: `AC…` ids hashed from case id (`_acc`) |
| `channel`, `flag` | SEED / GEN | Fixed pattern (IMPS in, UPI/ATM out) + canned flag strings |

### Investigation — graph (nodes & links)

Same split (SEED for `…4471`, GEN for others). Fixed 6‑node / 5‑edge topology
(victim → primary → 2 relays / cash‑out / linked); `id`s hashed, `balance` random,
`label`/`role`/`color`/`size`/`note` are fixed per role. **No graph field comes
from the CSV** (the real file has no counterparty column).

### Intelligence panel

| Field | Source | How |
|---|---|---|
| Risk signals (title, `pts`, evidence, formula, `rule`) — case `…4471` | **SEED** | 6 richly authored signals in `RISK_SIGNALS` (incl. invented `precision`/`trained`/device hashes) |
| Risk signals — other 5 cases | **MODEL** | `score_account` emits cards (pass‑through / fan‑in / structuring / Isolation‑Forest anomaly); `weight` from `RULE_CAPS`, `precision` `—`, `trained` `"2,000 txns (sample)"` |
| `total_score` | SEED (`91`) / MODEL | As above |
| `iob_pattern` (title/detail/extra) | SEED / GEN | Others: templated from `flag` + `_FLAG_STORY` |
| Summary EN / TA | SEED / GEN | Showcase authored; others templated (amount + ratio + flag) |

### Notes

| Field | Source | How |
|---|---|---|
| Initial notes (showcase only) | **SEED** | `INITIAL_NOTES` (1 system + 1 analyst) |
| New notes | **RUNTIME** | Typed by the user; @mentions resolved against `TEAM` |

### Notifications

| Field | Source | How |
|---|---|---|
| All 5 notifications | **SEED** | `INITIAL_NOTIFICATIONS` (deadline / mention / escalation / info) |

### Analyst confidence

| Field | Source | How |
|---|---|---|
| Confidence % | **RUNTIME** | Showcase seeded at `87`; others default `50` in the UI; slider writes to `Store` |

### STR draft

| Field | Source | How |
|---|---|---|
| Narrative — case `…4471` | **SEED** | `STR_DRAFT_NARRATIVE` (authored) |
| Narrative — other cases | **LLM** | OpenAI at generate time; **falls back** to the case summary if no key / on error/timeout |
| Entities, evidence chips, cite segments, compliance — `…4471` | **SEED** | `STR_ENTITIES` / `STR_EVIDENCE_CHIPS` / `STR_CITE_SEGMENTS` / `COMPLIANCE_ITEMS` |
| Entities / chips / compliance — other cases | **GEN** (derived) | Built from the bundle in `str_service` (chips from signal rules, entities from graph nodes, 3 fixed compliance items) |
| STR status, `fiu_reference` | **RUNTIME** | Status transitions on submit/file; reference minted on filing (`secrets` token) |
| Generation step labels | **SEED** | `GEN_STEPS` (progress UI only) |

### Audit trail

| Field | Source | How |
|---|---|---|
| Initial entries (showcase) | **SEED** | `AUDIT_LOG` (alert → create → claim → …) |
| New entries | **RUNTIME** | Appended on each action; `hash` = SHA‑256 chain in `audit_service` |

### Copilot (AI chat)

| Field | Source | How |
|---|---|---|
| Answers | **LLM** | OpenAI at runtime, grounded in the case bundle; labeled "not audit‑logged" |

### Header / session / model badge

| Field | Source | How |
|---|---|---|
| Current user, team roster | **SEED** | `CURRENT_USER`, `TEAM` |
| Model version / type / `is_placeholder` (ML info & health) | **MODEL** | Real — describes the detector fitted on the real CSV |

> **One‑line summary for the deck:** *the workstation is populated with SEED +
> GEN demo data (a realistic mock of a bank's CBS/CIF/ledger); the real CSV powers
> only the model's scores and signal points; the synthetic dataset is a pipeline‑
> only capability demo and never appears in the UI.*
