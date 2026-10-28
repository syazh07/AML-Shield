# Data Quality Report - mule_sample_data.csv

- **Transactions (rows):** 2000
- **Accounts (ACID):** 19
- **Customers (CIF_ID):** 19
- **Unique TRAN_ID:** 2000

## Zero-information columns (constant) -> dropped
- `TRAN_DATE` = `2026-05-19 18:30:00`
- `TRAN_TYPE` = `T`
- `TRAN_SUB_TYPE` = `CI`

## Time axis
- Unique TRAN_DATE values: **1** (range 2026-05-19 18:30:00 .. 2026-05-19 18:30:00)
- => **No real time axis.** Time-velocity / pass-through-timing / impossible-travel / unusual-hours features are NOT computable. We use count/ratio features instead.

## Graph feasibility
- Counterparty / beneficiary column present: **False**
- => **No account->account edges.** PageRank / betweenness / fan-in-fan-out cannot be built from this file. Deferred to roadmap.

## Usable signals
- PART_TRAN_TYPE (direction): {'C': 1837, 'D': 163}  <- strongest usable signal
- channel: {'UPI': 1971, 'NEFT': 12, 'IMPS_other': 6, 'MB': 4, 'BNA': 3, 'ATM': 3, 'IMPS': 1}
- TRAN_AMT: min=1, median=500, mean=1694, max=100000
- Txns in structuring band 45k-49,999: 2
- Txns >= 10 lakh (CTR single-txn): 0

## Caveats (treat with care)
- customer_age is 30 for 86% of rows -> likely imputed/default; weak feature.
- balance ranges -213607 .. 183494 and does not reconcile with amounts -> synthetic/shuffled; use cautiously.
- LIEN_AMT equals its median for 85% of rows -> near-constant injected value.

## Concentration
- Busiest account holds 1704/2000 (85%) of all transactions.
