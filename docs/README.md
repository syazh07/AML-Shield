# AML Shield — Documentation Index

What each document contains and when to read it.

## The documents

| Doc | What's in it | Read it when… |
|---|---|---|
| **[RUNNING.md](RUNNING.md)** | How to start the frontend, backend, and ML pipeline; ports/URLs; and a reference for every file the pipeline outputs (what each contains). | You want to run the project locally. |
| **[DATA_FLOW.md](DATA_FLOW.md)** | Architecture & data flow: how the pipeline and app connect, what each `ml_pipeline` file does, where the backend gets its data, the two data planes (model vs narrative), the real‑vs‑production mapping, and a **field‑by‑field provenance cheat‑sheet** (§9) for the jury. | You need to explain "where does this value come from?" or how the system is wired. |
| **[JURY_EXPLAINER.md](JURY_EXPLAINER.md)** | The demo walkthrough / pitch: the base‑rate problem, the workstation as the product, and the ML pipeline as the swappable plug (incl. the synthetic Tier‑B metrics). | Preparing or giving the jury demo. |
| **[THESIS.md](THESIS.md)** | The core argument/positioning — why the reviewer workstation, not the detector, is the product. | You want the "why" in one place. |
| **[WHITEPAPER.md](WHITEPAPER.md)** | The evidence base: the base‑rate fallacy, the $213B compliance‑cost research, regulatory context, and citations. | You need the research backing a claim. |
| **[METRICS_PRIMER.md](METRICS_PRIMER.md)** | The metrics explained — precision vs recall vs AUC, base‑rate math, and how to read the numbers. | A number in the deck needs justifying. |
| **[problem_statement.md](problem_statement.md)** | The original problem / requirements the project set out to solve (the full desired platform). | You want the starting brief. |
| **[../ml_pipeline/readme.md](../ml_pipeline/readme.md)** | The ML plan (v2): what the real sample supports (Tier A) vs the synthetic Tier‑B build, the modeling decisions, and a comparison with the original plan. | You want the modeling rationale. |
| **[archive/ml_plan.md](archive/ml_plan.md)** | The **superseded** original ML plan, kept for history. | Rarely — historical reference only. |

## Suggested reading order

- **New teammate:** [RUNNING.md](RUNNING.md) → [DATA_FLOW.md](DATA_FLOW.md) → [../ml_pipeline/readme.md](../ml_pipeline/readme.md) → [THESIS.md](THESIS.md).
- **Jury / reviewer:** [JURY_EXPLAINER.md](JURY_EXPLAINER.md) → [THESIS.md](THESIS.md) → [WHITEPAPER.md](WHITEPAPER.md) / [METRICS_PRIMER.md](METRICS_PRIMER.md), with [DATA_FLOW.md](DATA_FLOW.md) §9 on hand for "is this real or synthetic?" questions.

## Related, outside `docs/`

- `ml_pipeline/output/` — generated reports (see the output reference in [RUNNING.md](RUNNING.md) §4).
- `aml-dashboard/backend/README.md` — backend quick start + endpoint list.
