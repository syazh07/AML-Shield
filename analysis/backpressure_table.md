# Reviewer Backpressure Model

*Numbers anchored to `WHITEPAPER.md`. All inputs live in the ASSUMPTIONS block of `analysis/backpressure.py` and are meant to be adjusted.*

## 1. Precision collapses when the target is rare (base-rate fallacy)
Per **100,000 transactions/day**, model held at **95% sensitivity** and **3% false-positive rate**; only the base rate of illicit activity changes:

| Base rate | True positives | False positives | Total alerts | **Precision (PPV)** |
|---|---|---|---|---|
| 0.1% | 95 | 2,997 | 3,092 | **3.1%** |
| 1.0% | 950 | 2,970 | 3,920 | **24.2%** |
| 10.0% | 9,500 | 2,700 | 12,200 | **77.9%** |
| 50.0% | 47,500 | 1,500 | 49,000 | **96.9%** |

> At the FinCrime-real **0.1%** base rate, precision is **~3.1%** -- **~97 of every 100 alerts are false**. This matches the industry's documented 85-95% false-positive rate. You cannot out-model arithmetic.

## 2. What that does to the review team
Per **10,000 alerts/day** at the industry **90%** false-positive rate, **30 min** per review:

- False-positive alerts/day: **9,000**
- Analyst-hours/day wasted on noise: **4,500**
- Equivalent staffing on noise alone: **~900 full-time analysts** (8h/day, 230 working days/yr)

## 3. Two ways to fix it -- and which wins
Legacy operating point: 10,000 alerts/day, 30 min each.

| Strategy | Alerts/day | Review-hours/day | Analysts (FTE) | Saving |
|---|---|---|---|---|
| Legacy tooling (30 min) | 10,000 | 5,000 | 625 | -- |
| **Hard model win** (-50% false positives, still 30 min) | 5,500 | 2,750 | 344 | 45% |
| **AML Shield workstation** (same alerts, 9 min = -70% review time) | 10,000 | 1,500 | 188 | 70% |

- A hard model win (halving false positives) saves **45%** of review hours.
- The workstation saves **70%** -- on the *same* alerts, no model change -- a **3.3x** throughput gain, matching the whitepaper's cited ~70% copilot productivity.
- They **stack**: HSBC + Google Cloud paired explainable workflows with ML for **2-4x more true positives and >60% fewer false positives**.

> Detection is a plug-in. Review capacity is the business. AML Shield attacks the term that dominates the cost.
