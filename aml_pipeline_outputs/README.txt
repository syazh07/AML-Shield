AML Shield — ML pipeline outputs
================================

real/       Tier-A on the real IOB sample (2000 txns / 19 accounts).
            Unsupervised: transparent rules ⊕ Isolation Forest → 0–100 composite, with SHAP.
            No labels exist, so validation uses planted mule-vs-normal separation + seed stability.

synthetic/  Tier-B on a jury-approved LABELED synthetic scenario (330 accounts, with
            timestamps + counterparty edges). Supervised XGBoost + graph centrality + temporal
            features. Metrics are CAPABILITY, not production performance (known generative process).

Hero files
----------
flagged_mule_accounts(.csv / _synthetic.csv)  — the ranked deliverable
validation_report(.md / _synthetic.md)        — metrics (synthetic: ROC-AUC 0.996, PR-AUC 0.982)
risk_ranking.png                               — real risk ranking chart
roc_pr_synthetic.png                           — synthetic ROC + PR curves

The real sample is the reality anchor; synthetic demonstrates the full platform capability.
