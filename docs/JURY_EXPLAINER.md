# AML Shield — Jury Walkthrough
### Finding the mule is the easy half. We rebuilt the hard half: the review.

> **Thesis in one line:** anyone can hand you a detector — RBI already published
> one, and we built one in an afternoon. What nobody fixed is what happens *after*
> an alert fires, where mule-fighting actually breaks. AML Shield rebuilds that.
> (Full argument: `THESIS.md`. Evidence base: `WHITEPAPER.md`. Metrics explained:
> `METRICS_PRIMER.md`.)

---

## 1. The problem behind the problem

Mule accounts launder money for cyber-fraud and organised crime. The instinct is
to build a better detector. But detection at bank scale runs into hard arithmetic:
**mules are rare, so even a near-perfect model produces alerts that are mostly
false**, and each false alert still lands on a human analyst who must clear it
before the 7-day RBI reporting clock runs out.

Per 100,000 transactions/day, a strong model (95% sensitivity, 3% false-positive
rate) at the FinCrime-real 0.1% base rate produces:

| Base rate | Total alerts | **Precision** | Alerts that are FALSE |
|---|---|---|---|
| **0.1% (reality)** | 3,092 | **3.1%** | **~97%** |
| 1.0% | 3,920 | 24.2% | 76% |

At the real base rate, **~97 of every 100 alerts an analyst opens are innocent
customers** — matching the documented industry **85–95% false-positive rate**.
This is the **base-rate fallacy**, and no realistic model escapes it. So the
binding constraint isn't model quality — it's **how fast a human can clear an
alert.**

---

## 2. Where the money (and time) actually goes

Global FinCrime compliance already costs **~$213B/year, ~79% of it labor**. Per
10,000 alerts/day at the industry 90% false rate, 30 min/review, that's **4,500
wasted analyst-hours/day ≈ ~900 full-time analysts clearing pure noise.** The lever
that matters:

![Review-hours: workstation vs a hard model win](analysis/backpressure_chart.png)

| Strategy | Review-hours / day | Analysts (FTE) | Saving |
|---|---|---|---|
| Legacy tooling (30 min/alert) | 5,000 | 625 | — |
| A **hard model win** (−50% false positives) | 2,750 | 344 | 45% |
| **AML Shield workstation** (9 min/alert) | 1,500 | 188 | **70%** |

A major ML breakthrough saves 45%. Making each review faster saves **70% — same
alerts, no model change** — a **3.3× throughput gain**, matching the cited ~70%
AI-copilot productivity figure. And they **stack**: HSBC + Google Cloud paired
explainable workflows with ML for **2–4× more true positives and >60% fewer false
positives**. (Numbers from `analysis/backpressure.py`; every assumption is tunable.)

**This is not theoretical.** Recent mega-fines are *workflow* failures: **TD Bank
$3B** (capped alerts, 70k backlog), Capital One $390M (alert-fatigue auto-close),
and — the IOB-relevant one — **Paytm Payments Bank's RBI license revocation over a
single PAN tied to multiple mule accounts.** The failure was human review capacity,
not a missing model.

---

## 3. The hero — the investigator workstation (`project/`)

A React + FastAPI application that collapses a 30-minute review to 9 minutes.
Everything an analyst needs is on one screen:

| Capability | What the reviewer gets |
|---|---|
| **Case pool & lifecycle** | Claim / hand off / escalate, with live STR deadline clocks so no case breaches the 7-day window |
| **Money-flow replay** | Graph + timeline + a **time scrubber** — the analyst *watches* the fan-out happen, second by second |
| **Evidence-linked signals** | Each risk signal shows its formula, model weight **and precision** — why it fired and how much to trust it |
| **Case Copilot** | Ask "what triggered this?" — it answers *and highlights the exact node/edge in the graph* |
| **One-click STR** | Auto-drafts the regulatory report, every sentence **citation-linked to graph evidence**, plus a compliance checklist |
| **Bilingual EN/Tamil** | Summaries in the language IOB's staff actually use |
| **Immutable audit hash-chain** | Every action logged for RBI inspection |

The compliance checklist even catches nuance a rushed analyst would miss —
e.g. *"₹4.9L is below the ₹10L threshold; file on pattern grounds instead."* That
is the difference between a tool that scores and a tool that **helps a human
decide.**

**The architectural tell:** the backend's ML service uses the model as a plugin
behind a fixed interface. We *designed* the model as a swappable plug — RBI's MuleHunter.AI,
Actimize's, or ours all drop in unchanged. The workstation is the product; the
model is a component.

---

## 4. The supporting act — yes, we can also produce a model (`ml_pipeline/`)

To prove the "model is a plug" claim, we built a complete, compliant, explainable
detector from the raw sample data in one sitting:

![Risk ranking](ml_pipeline/output/risk_ranking.png)

- **Hybrid design:** a transparent, auditable rule engine (6 IOB mule typologies)
  fused with an **Isolation Forest** anomaly model → a 0–100 composite, every score
  decomposed into named reasons + **SHAP**.
- **Two honest tiers.** The real 19-account sample has **no labels, no usable
  timestamps, and no counterparty links**, so on it we ship exactly what it
  supports — rules ⊕ Isolation Forest, the unsupervised **reality anchor**.
- **Synthetic scenario unlocks the full stack.** With the jury's go-ahead we added
  a **labeled** synthetic dataset that supplies the three missing inputs — labels,
  real timestamps, and counterparty edges — turning the roadmap into a live demo:
  **XGBoost** (supervised), **temporal** features (velocity, pass-through timing),
  and **graph centrality** (PageRank, fan-in/out via networkx).
- **Real metrics, honestly bounded.** On the synthetic tier the supervised model
  scores **ROC-AUC 0.996 · PR-AUC 0.982 · 5-fold CV 0.997 ± 0.004** (precision 0.94 /
  recall 0.92). Because that data has a *known generative process*, we report these
  as **capability, not production performance** — the real sample stays the anchor.
- **Validated both ways:** the real path by injecting known mules vs known-normals
  (cleanly separated — mules 85.8 / 65.2 vs normals 49.8 / 19.9; ranking stable at
  τ = 0.84); the synthetic path by actual ROC / PR curves against ground-truth labels.

The point for the jury: **this took an afternoon and is interchangeable with RBI's
model.** The detector is the commodity. Everything in §3 is not.

---

## 5. What we're honest about

- The `ml_pipeline` anchors on a tiny 19-account real sample — a proof, not a
  production model — augmented by a **labeled synthetic scenario** for the
  supervised / graph / temporal capability demo (those metrics are *capability, not
  production truth*). Real deployment plugs in the bank's trained model.
- The workstation is fully wired to the backend, running on real SQLite persistence with live STR generation via OpenAI.
- The backpressure numbers are illustrative and fully parameterised — they make a
  structural point (base rate dominates), not a precise forecast.

---

## 6. The closing line

> Detection finds the needle. We built the **workbench** that lets a human pull it
> out — **3.3× faster** — before the clock runs out. Everyone else is sharpening
> the magnet. We fixed the haystack-handling. **Finding was only part of the
> problem; the review is the product.**

---

### File map
| File | What it is |
|---|---|
| `THESIS.md` | The positioning argument (north star) |
| `WHITEPAPER.md` | The full, cited evidence base (base-rate fallacy, $213B, fines) |
| `METRICS_PRIMER.md` | Precision / recall / specificity / base-rate, plain-English |
| `analysis/backpressure.py` + `backpressure_table.md` | The cost model behind every number |
| `project/` | The investigator workstation (the product) |
| `ml_pipeline/` | Our own detector (proof the model is a plug) |
| `my_ml_plan.md` | The modelling plan + perspectives comparison |
