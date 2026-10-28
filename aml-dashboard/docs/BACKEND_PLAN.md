# AML Shield — Backend Plan

This document describes the FastAPI backend for AML Shield. The React frontend is now **fully wired to this API**, using SQLite for persistence.

## Goals

| Priority | Capability | Approach |
|----------|------------|----------|
| P0 | REST API skeleton | FastAPI + Pydantic schemas aligned with frontend entities |
| P0 | STR draft generation | OpenAI API (`openai` Python SDK) with structured prompts |
| P1 | Case lifecycle mutations | Claim, handoff, close, escalate, notes, confidence |
| P1 | Immutable audit trail | Append-only log with hash chaining |
| P2 | ML risk scoring | **Plugin Integration** — swappable service interface calling real ML model |
| P3 | Persistence | SQLite first, Postgres later |
| P3 | Auth / RBAC | JWT + role checks (analyst, senior, compliance) |

## Architecture

```
┌─────────────────┐     HTTP/JSON      ┌──────────────────────────────────┐
│  React frontend │ ─── (future) ────► │  FastAPI (backend/app/main.py)   │
│  (mock data)    │                    │                                  │
└─────────────────┘                    │  ┌────────────┐  ┌─────────────┐ │
                                       │  │ CaseService│  │ AuditService│ │
                                       │  └─────┬──────┘  └──────┬──────┘ │
                                       │        │                  │       │
                                       │  ┌─────▼──────┐  ┌───────▼─────┐ │
                                       │  │ STRService │  │ MLScoring   │ │
                                       │  │ (OpenAI)   │  │ (generic)   │ │
                                       │  └────────────┘  └─────────────┘ │
                                       └──────────────────────────────────┘
```

## Tech stack

- **Runtime:** Python 3.11+
- **API:** FastAPI, Uvicorn
- **Validation:** Pydantic v2
- **STR / LLM:** `openai` SDK (GPT-4o or configurable model)
- **Config:** `pydantic-settings`, `.env`
- **ML (later):** Replace `GenericMLScoringService` with real model server (ONNX, SageMaker, etc.)

## Domain modules

### 1. Cases (`/api/v1/cases`)

Mirrors `CASES` in constants. Supports list/filter, detail, claim, handoff, close, escalate.

Investigation reads (scoped by `case_id`):

- Account profile, timeline, graph, risk signals, bilingual summary
- Related cases (device / account cross-links)

### 2. STR (`/api/v1/cases/{case_id}/str`)

Status machine: `none` → `drafting` → `review` → `filed`

| Endpoint | Purpose |
|----------|---------|
| `POST .../str/generate` | Start async STR generation job |
| `GET .../str/generate/{job_id}` | Poll generation steps |
| `GET .../str` | Current draft |
| `PUT .../str` | Update narrative, entities, evidence chips |
| `POST .../str/submit-review` | Move to `review` |
| `POST .../str/file` | Mark `filed`, return FIU reference |

**OpenAI flow**

1. Gather case context: risk signals, timeline, graph nodes, account profile, analyst confidence, linked cases.
2. Run pipeline steps (matches frontend UX):
   - Extract risk signals
   - Load transaction evidence
   - Cross-reference device data
   - Compose narrative (OpenAI)
   - Populate entity fields (structured output + heuristics)
3. Return draft with `narrative`, `cite_segments`, `evidence_chips`, `entities`, `compliance_items`.

If `OPENAI_API_KEY` is missing, the service falls back to seeded narrative from mock data (dev mode).

### 3. ML scoring (`/api/v1/ml`)

**Plugin Integration** — The service integrates the real ML scoring model as a swappable plugin.

```python
class MLScoringService(Protocol):
    async def score_transaction(self, payload: TransactionFeatures) -> RiskScoreResult: ...
    async def score_case(self, case_id: str) -> CaseScoreResult: ...
```

Current implementation:

- Integrates the ML model as a swappable plugin.
- Returns `model_version`, `confidence`, `signals[]`, `explanation`
- Capable of running live inferences against the provided model

Future options: batch scoring from TM engine, graph embeddings, device fingerprint model.

### 4. Audit (`/api/v1/cases/{case_id}/audit`)

Append-only entries: `ts`, `actor`, `action`, `hash`. Every mutation should call `AuditService.append()`.

### 5. Notifications (`/api/v1/notifications`)

List, mark read, dismiss. Created by handoffs, mentions, deadlines, escalations.

## Data layer (phased)

| Phase | Storage | Notes |
|-------|---------|-------|
| **Now** | In-memory + seed from `backend/app/data/seed.py` | Same shapes as `constants.js` |
| **Next** | SQLite via SQLAlchemy | Cases, STR drafts, audit, notifications |
| **Prod** | PostgreSQL | Multi-tenant, FIU export archive |

## Environment variables

See `backend/.env.example`:

- `OPENAI_API_KEY` — required for live STR generation
- `OPENAI_MODEL` — default `gpt-4o`
- `API_PREFIX` — default `/api/v1`
- `CORS_ORIGINS` — Vite dev server when frontend connects

## Integration with frontend (completed)

The frontend is now fully integrated with these API contracts.

1. Point Vite proxy at `http://localhost:8000`
2. Replace `CASES` import with `GET /api/v1/cases`
3. Wire STR generate button to `POST .../str/generate` + poll
4. Wire ActionModal mutations to POST endpoints
5. Add auth headers

## Security (production checklist)

- [ ] JWT auth + role-based endpoint guards
- [ ] Rate limit STR generation (OpenAI cost)
- [ ] PII redaction in logs
- [ ] Encrypt PAN/mobile at rest
- [ ] Audit hash chain verification endpoint
- [ ] FIU-IND XML export signing

## Local development

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # add OPENAI_API_KEY
uvicorn app.main:app --reload --port 8000
```

OpenAPI docs: http://localhost:8000/docs
