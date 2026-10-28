# Metrics Primer — the words you need to own on stage

This is the vocabulary the whole pitch stands on. If a judge asks "what's your
precision?" and you fumble, the thesis wobbles. Learn these six ideas and the
one fallacy at the end — that's the entire game. Numbers here match
`WHITEPAPER.md` and `analysis/backpressure.py` exactly.

Everything below uses one running example so the numbers connect:

> **Setup:** IOB screens **40,000,000** accounts. About **0.1%** are truly mule
> → **40,000 real mules** and **39,960,000 clean accounts**. Our model catches
> **95%** of mules (recall) and wrongly flags **3%** of clean accounts (FPR) —
> the whitepaper's canonical operating point.

---

## 1. The four outcomes (the confusion matrix)

Every account the model judges lands in one of four boxes:

| | Model says **MULE** | Model says **clean** |
|---|---|---|
| **Actually mule** | ✅ True Positive (TP) — caught it | ❌ False Negative (FN) — **missed a criminal** |
| **Actually clean** | ❌ False Positive (FP) — **false alarm** | ✅ True Negative (TN) — correctly ignored |

In our example:
- **TP = 38,000** (95% of 40,000 mules caught)
- **FN = 2,000** (5% slipped through)
- **FP = 1,198,800** (3% of 39.96M clean accounts wrongly flagged)
- **TN = 38,761,200** (the rest, correctly left alone)

The two "❌" boxes are the two ways to be wrong, and they hurt *different* people:
FN lets a criminal operate; FP drags an innocent customer (and an analyst) into
an investigation. You cannot minimise both at once — that's the tradeoff below.

---

## 2. The six terms

**Recall (a.k.a. Sensitivity, True Positive Rate)** — *of the real mules, what
fraction did we catch?*
> `Recall = TP / (TP + FN) = 38,000 / 40,000 = 95%`
Miss-rate is the flip side (5%). High recall = few criminals escape. Regulators
care about this: missing mules is a compliance failure.

**Specificity (True Negative Rate)** — *of the clean accounts, what fraction did
we correctly leave alone?*
> `Specificity = TN / (TN + FP) = 38,761,200 / 39,960,000 = 97%`
Sounds great — 97%! Hold that thought; §3 shows why it's not enough.

**False Positive Rate (FPR)** — *of the clean accounts, what fraction did we
wrongly flag?* Simply `1 − Specificity = 3%`. This is the false-positive number
that generates the alert flood — the whole reason reviewers drown.

**Precision (Positive Predictive Value, PPV)** — *of the accounts we flagged, what
fraction were actually mules?*
> `Precision = TP / (TP + FP) = 38,000 / 1,236,800 = 3.1%`
**This is the reviewer's real experience.** 3.1% precision means **~97 of every 100
alerts an analyst opens are innocent people.** This number, not accuracy, is what
determines whether your review team drowns — and it matches the documented industry
85–95% false-positive rate.

**Accuracy** — *what fraction of all judgements were correct?* `(TP+TN)/total`.
Here accuracy ≈ **97%** — sounds like a triumph, and is **completely misleading**.
A model that flags *nobody* scores **99.9%** accuracy (it's "right" about all
39.96M clean accounts) while catching zero mules — i.e. the useless model *beats*
the useful one on accuracy. Never quote accuracy for rare-event problems (§4).

**F1 score** — the harmonic mean of precision and recall, one number when you want
to balance the two: `2·P·R / (P+R) ≈ 2·0.031·0.95 / (0.031+0.95) ≈ 0.06`. Useful
for comparing models; not something a judge feels intuitively.

---

## 3. The precision–recall tradeoff (why you can't just "tune it up")

A model outputs a *risk score*; you pick a **threshold** to flag above. Move it:

- **Threshold lower** → flag more accounts → **recall ↑** (catch more mules) but
  **precision ↓** (more false alarms). More work for reviewers.
- **Threshold higher** → flag fewer → **precision ↑** but **recall ↓** (miss
  mules). Compliance risk.

So "just make the model stricter" trades a criminal you miss for an analyst-hour
you save, and vice versa. There is no free lunch **inside the model**. The only
way to win *both* is to make each alert cheaper to review — which is the product.

---

## 4. The base-rate fallacy — the heart of the whole pitch

Here is the counter-intuitive fact judges will remember:

> **When the thing you're hunting is rare, even a near-perfect model produces
> alerts that are mostly false — because the enormous clean population throws off
> a flood of false positives that swamps the few true ones.**

Same model (95% sensitivity, 3% FPR), per 100,000 transactions/day — only the base
rate of illicit activity changes (this is the whitepaper's canonical table):

| Base rate | Total alerts | **Precision (PPV)** | Alerts that are WRONG |
|---|---|---|---|
| **0.1% (FinCrime reality)** | 3,092 | **3.1%** | **~97%** |
| 1.0% | 3,920 | 24.2% | 76% |
| 10.0% | 12,200 | 77.9% | 22% |
| 50.0% | 49,000 | 96.9% | 3% |

At the real 0.1% base rate, **~97 of every 100 alerts are false.** The clean pile
is so much bigger than the mule pile that a small error rate on it buries the
signal. This is why **accuracy lies**, and why the entire industry sits at 85–95%
false positives — it's arithmetic, not bad engineering.

**The takeaway line for the jury:** *"You cannot out-model the base rate. A better
detector shaves the false pile a little; it never empties it. So the real question
isn't 'how good is the model' — it's 'how fast can a human clear an alert.' That's
what we built."*

---

## 5. One-glance cheat sheet

| Term | Question it answers | Formula | Who cares |
|---|---|---|---|
| Recall / Sensitivity | Of real mules, % caught | TP/(TP+FN) | Regulator (missed crime) |
| Specificity | Of clean, % correctly cleared | TN/(TN+FP) | — (looks good, misleads) |
| FPR | Of clean, % wrongly flagged | FP/(FP+TN) = 1−Spec | Source of the alert flood |
| **Precision / PPV** | Of alerts, % that are real | **TP/(TP+FP)** | **Reviewers (the pitch)** |
| Accuracy | Of all, % correct | (TP+TN)/all | Nobody — hides rare-event failure |
| F1 | Balance of P and R | 2PR/(P+R) | Model comparison |

**If you remember one thing:** high specificity + rare positives ⇒ **low
precision** ⇒ reviewers buried. The model is not the bottleneck; the review is.
