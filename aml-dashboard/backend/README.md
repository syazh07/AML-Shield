# AML Shield Backend

FastAPI service for case management, STR generation (OpenAI), and generic ML scoring.

## Quick start

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# Add OPENAI_API_KEY to .env for live STR narratives (optional — falls back to seed data)
uvicorn app.main:app --reload --port 8000
```

- Swagger UI: http://localhost:8000/docs
- Health: http://localhost:8000/api/v1/health

## Key endpoints

| Area | Endpoint |
|------|----------|
| Cases | `GET /api/v1/cases` |
| STR generate | `POST /api/v1/cases/{id}/str/generate` |
| STR poll | `GET /api/v1/cases/{id}/str/generate/{job_id}` |
| ML stub | `POST /api/v1/ml/score/case/{id}` |

See [../docs/BACKEND_PLAN.md](../docs/BACKEND_PLAN.md) for full architecture.
