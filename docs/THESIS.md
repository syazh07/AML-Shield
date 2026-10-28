# AML Shield — The Thesis
### Detection is commoditized. The review is the bottleneck. We rebuilt the review.

> Full evidence base with citations: `WHITEPAPER.md`. Metrics explained:
> `METRICS_PRIMER.md`. Cost model behind every number: `analysis/backpressure.py`.

---

## The one sentence

> Everyone in this room can hand you a mule-detection model — RBI already
> published one. **Nobody has fixed what happens after the model fires an alert.**
> That's where mule-fighting actually breaks, and that's what AML Shield rebuilds.

---

## 1. The claim everyone else is making (and why it's the easy half)

The obvious hackathon answer is "build a better detector" — XGBoost, an LSTM, a
graph model. We built one too (see `ml_pipeline/`), and it works. But detection
is now a **commodity**:

- **RBI has released a model (MuleHunter.AI).** A capable baseline is already in the public domain.
- The libraries are open-source and an afternoon of work (our own pipeline proves
  this — six scripts, one sitting).
- Our architecture treats the model as a **swappable plug**: the backend implements a
  `GenericMLScoringService` that integrates the model as a plugin behind a
  fixed interface. Any bank's model — RBI's MuleHunter.AI, Actimize's, ours — drops in unchanged.

If the model is a plug that anyone can supply, **the model is not the moat.**

---

## 2. The half nobody solved: the alert lands on a human

The moment detection succeeds, it creates a problem: **an alert a person must
clear.** And here the mathematics turns against you.

Mules are **rare** — illicit funds are ~2–5% of GDP and a far smaller slice of
transaction *count*. When positives are rare, **precision** (the share of alerts
that are actually mules) collapses, no matter how good the model is. This is the
**base-rate fallacy**. Per 100,000 transactions/day, a strong 95%-sensitivity /
3%-FPR model gives:

| Base rate of illicit activity | Total alerts | **Precision (PPV)** | Alerts that are FALSE |
|---|---|---|---|
| **0.1% (FinCrime reality)** | 3,092 | **3.1%** | **~97%** |
| 1.0% | 3,920 | 24.2% | 76% |
| 10.0% | 12,200 | 77.9% | 22% |
| 50.0% | 49,000 | 96.9% | 3% |

Read the top row: at the real-world base rate, **~97 of every 100 alerts an analyst
opens are innocent customers.** This isn't a bug — it matches the documented
**industry 85–95% false-positive rate** (McKinsey: >90%). Pushing the model
*stricter* to cut false alarms just makes it miss real mules (the precision–recall
tradeoff). **The pain is structural — you cannot out-model arithmetic.**

---

## 3. Where the cost actually lives

Global financial-crime compliance already costs **~$213 billion/year**, and it's
**~79% labor vs ~9% technology** — i.e. it's a *review-time* problem wearing a
technology badge. Concretely, per 10,000 alerts/day at the industry 90% false rate,
30 min/review:

- **4,500 analyst-hours/day wasted on noise → ~900 full-time analysts** doing
  nothing but clearing false positives.

Now compare the two ways to reduce that (numbers from `analysis/backpressure.py`,
fully tunable):

| Strategy | What it takes | Review-hrs/day | Analysts (FTE) | Saving |
|---|---|---|---|---|
| Legacy tooling | — | 5,000 | 625 | — |
| **A hard model win** — halve false positives | months of ML R&D | 2,750 | 344 | 45% |
| **AML Shield workstation** — 30 min → 9 min/alert | better *review UX* | 1,500 | 188 | **70%** |

![Review-hours: workstation vs model](analysis/backpressure_chart.png)

A **major** modelling breakthrough (50% fewer false alerts) saves 45%. Making each
review faster saves **70% — on the same alerts, with no model change at all** — a
**3.3× throughput multiplier**, matching the whitepaper's cited *~70% AI-copilot
productivity gain*. And they **stack**: HSBC + Google Cloud paired explainable
workflows with ML and found **2–4× more true positives while cutting false
positives >60%**. **The review time is the dominant term in the cost function, and
it's the term nobody optimises.**

---

## 4. This is not theoretical — regulators are fining the backlog

Every recent mega-penalty is a *workflow* failure, not a detection failure:

| Institution | Year | Penalty | Root cause |
|---|---|---|---|
| **TD Bank** | 2024 | **$3.0B** | Capped alerts to save cost; 70,000-alert backlog; 92% of volume unmonitored |
| Capital One | 2021 | $390M | Alert fatigue → auto-closing alerts without review |
| NatWest | 2021 | £264M | Drowned in noise; ignored blatant cash laundering |
| **Paytm Payments Bank** | 2024 | **License revoked (RBI)** | **Single PAN linked to multiple mule accounts** — onboarding outpaced human diligence |

The Paytm case is your exact problem, with a live Indian precedent: the failure was
**human capacity to review**, not the absence of a model. A 30-day+ alert backlog
is regulators' single best predictor of a failing AML program.

---

## 5. What we built instead — the investigator workstation

The whitepaper prescribes exactly three fixes — **graph visualization, a
generative-AI copilot, and explainable ML workflows.** AML Shield (`project/`) is
all three, purpose-built for IOB and for the 30→9 minute collapse:

- **Case pool & lifecycle** — claim, hand off, escalate, with live STR deadline
  clocks so nothing breaches the 7-day RBI window.
- **Money-flow replay** — graph + timeline + a **time scrubber** that plays the
  laundering back second-by-second. The analyst *watches* the fan-out happen.
- **Evidence-linked risk signals** — every signal carries its formula, model weight
  *and precision*, so the reviewer sees why it fired and how much to trust it.
- **Case Copilot** — ask "what triggered this?" and it answers *and highlights the
  exact node/edge in the graph.*
- **One-click STR** — auto-drafts the report with every sentence **citation-linked**
  to graph evidence, plus a compliance checklist that catches subtleties (e.g.
  "₹4.9L is *below* the ₹10L threshold — file on pattern grounds").
- **Bilingual (English/Tamil)** summaries; **immutable audit hash-chain** for RBI.

---

## 6. Why this wins the argument

| The commodity pitch | Our pitch |
|---|---|
| "Our model scores 0.9x AUC" | "Your model is welcome here — it's a plug" |
| Optimises the term that's already ~solved | Optimises the term that dominates cost (review time) |
| Ignores the reviewer | Is built entirely for the reviewer |
| One more detector | The system that makes *any* detector usable at scale |

**Detection finds the needle. We built the workbench that lets a human actually
pull it out — 3.3× faster — before the 7-day clock runs out.** Finding was only
part of the problem. The review is the product.

---

### Supporting artifacts
- `WHITEPAPER.md` — the full, cited evidence base (base-rate fallacy, $213B, fines)
- `analysis/backpressure.py` — the model behind every number here (tune and re-run)
- `METRICS_PRIMER.md` — precision / recall / specificity / base-rate, plain-English
- `ml_pipeline/` — our own detector, proving the "model is a plug" claim
- `project/` — the workstation itself (React + FastAPI)
- `JURY_EXPLAINER.md` — the full walkthrough
