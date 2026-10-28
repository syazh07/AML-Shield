# AML Shield — Investigator Workstation

React + Vite frontend and a FastAPI backend for AML mule-case investigation:
case pool, graph/timeline investigation, STR drafting, notifications, audit trail.
The detection model is a **swappable plug** (`GenericMLScoringService`) — the product
is the review workflow. See `../THESIS.md` / `../docs/THESIS.md` for the why, and
`PENDING.md` for what's done vs outstanding.

## Architecture

```
React (Vite, :5173) ──/api proxy──▶ FastAPI (:8000) ◀── seeder.py (demo activity)
   polls every 5s                    in-memory state
```

Frontend and backend are separate. The frontend **polls** the API, so anything the
seeder pushes shows up within a few seconds — no websockets, clean separation.

## Run the live demo (3 terminals)

**1 — Backend**
```bash
cd backend
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env          # optional: add OPENAI_API_KEY for live STR narratives
uvicorn app.main:app --reload --port 8000
```
Swagger: http://localhost:8000/docs · Health: http://localhost:8000/api/v1/health

**2 — Frontend**
```bash
npm install
npm run dev                   # http://localhost:5173
```

**3 — Seeder (makes it feel alive — trigger when you want)**
```bash
cd backend && source .venv/bin/activate
python seeder.py                       # stream a new event every ~4s (Ctrl+C to stop)
python seeder.py --mode burst --count 8   # inject a quick burst and exit
python seeder.py --interval 8             # slower stream
```
Watch the case pool count climb, notifications fire, and teammates claim/close cases.

**Reset between demo runs** — after a demo, restore the clean base state:
```bash
cd backend && source .venv/bin/activate
python reset_db.py            # live reset via POST /admin/reset (no restart needed)
```

## Notes
- **Python:** the backend targets 3.11+. It also runs on 3.9/3.10 via
  `eval_type_backport` (already in `requirements.txt`).
- **Persistence:** state is stored in SQLite (`backend/aml_shield.db`, gitignored) and
  survives restarts. Use `python reset_db.py` to return to the seeded base state.
- **OpenAI key optional:** without it, STR generation returns a seeded narrative.
