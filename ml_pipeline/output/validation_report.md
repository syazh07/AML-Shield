# Validation Report

## 1. Separation test (planted normals vs planted mules)
Two known-normal and two known-mule accounts were injected, then scored.

| Planted account | Type | Rank (of 23) | Composite | Flagged (>=60) |
|---|---|---|---|---|
| MULE_STRUCT | MULE | 1 | 85.8 | YES |
| MULE_PASSTHRU | MULE | 10 | 65.2 | YES |
| NORMAL_1 | normal | 21 | 49.8 | no |
| NORMAL_2 | normal | 23 | 19.9 | no |

- Every planted MULE outranks every planted NORMAL: **True**
- Every planted MULE flagged (>=60): **True**
- Every planted NORMAL below threshold (<60): **True**

**Result: PASS** - the detector separates mules from normal accounts and the fixed cutoff lands between the two groups.

## 2. Isolation Forest ranking stability across seeds
- Mean pairwise Kendall's tau across 5 seeds: **0.837** (1.0 = identical ranking).
- High agreement => the anomaly component is stable, not seed-luck.
