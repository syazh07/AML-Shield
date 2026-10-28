# Data Quality Report - synthetic_scenario.csv

- **Transactions (rows):** 9481
- **Accounts (ACID):** 330
- **Labelled mules / normals:** 65 / 265

## Tier-B input gate
- Real time axis present (TRAN_DATE varies): **True** (9476 distinct timestamps)
- Counterparty edges present (BENEFICIARY_ACID): **True**
- Ground-truth label present (is_mule): **True**

**Gate: PASS** — supervised + temporal + graph features are computable on this dataset.

> Synthetic data has a *known generative process*; metrics on it demonstrate capability, not production performance. The real 19-account sample remains the unsupervised reality anchor.

## Typology mix (planted)
- `normal`: 255 accounts
- `ambiguous`: 30 accounts
- `new_account_burst`: 12 accounts
- `structuring`: 11 accounts
- `pass_through`: 9 accounts
- `micro_credit_flood`: 8 accounts
- `fan_in_aggregation`: 5 accounts
