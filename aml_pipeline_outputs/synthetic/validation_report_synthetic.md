# Validation Report — Synthetic Scenario (supervised)

> Synthetic data has a **known generative process**. These metrics demonstrate the model's *capability* when labels exist; they are NOT a claim about production performance. The real 19-account sample stays the unsupervised anchor.

- Accounts: **330**  (65 mules / 265 normals)
- Model: XGBoost, 28 features (base + temporal + graph), out-of-fold predictions

## Discrimination (out-of-fold)
- **ROC-AUC: 0.996**
- **PR-AUC (average precision): 0.982**
- 5-fold CV ROC-AUC: **0.997 ± 0.004**
- Not-trivially-separable check: ROC-AUC < 1.0 → **OK**

## Classification @ threshold 0.5
- Precision **0.938** · Recall **0.923** · F1 **0.930**

| | pred normal | pred mule |
|---|---|---|
| **actual normal** | 261 | 4 |
| **actual mule** | 5 | 60 |

## Real-anchor sanity check
- Busiest real account (`b8b3e9f99f…`, the 1704-txn aggregator) ranks **#5 of 19** under the unchanged unsupervised hybrid.
- Anchor intact (flagged ≥60 **and** top third): **True** — the synthetic/supervised work did not disturb the real detector (its `account_scores.csv` stays byte-identical).
