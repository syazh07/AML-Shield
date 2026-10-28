# AML Shield Dashboard — Pending Work

_Review date: 2026-07-24. Scope: `aml-dashboard/` (React frontend + FastAPI backend)._

## Status in one line
The frontend and backend are now **wired together** (case pool + notifications poll
the live API), a **triggerable seeder** makes the dashboard feel alive, and the
critical backend bugs are fixed. Remaining gaps are deeper features (full
investigation-per-case, STR wiring, persistence, auth) — see below.

## ✅ Done in this pass (2026-07-24)
- **Frontend ↔ backend connected.** Vite proxy + `src/lib/api.js`; `App.jsx` fetches
  and **polls** cases + notifications every 5s (seed constants remain an offline
  fallback). Claim and notification read/dismiss now hit the API.
- **`datetime` bug fixed** — `POST /cases/{id}/notes` works.
- **Real notification state** — `NotificationService` with working read / mark-all /
  dismiss, and auto-emitted notifications on new case / close / escalate.
- **Case lifecycle completed** — `POST /cases` (ingest), `close`, `handoff`,
  `escalate` endpoints added.
- **Live seeder** — `backend/seeder.py`, triggerable, streams new cases + teammate
  activity into the running API. Backend verified end-to-end on Python 3.9
  (added `eval_type_backport` + deferred annotations for compatibility).

## ✅ Already solid (the baseline)
- Rich, complete-feeling frontend UX: case pool, investigation (graph + timeline +
  scrubber replay), intelligence panel, STR drawer, notifications, bilingual summaries.
- Clean backend architecture: FastAPI, Pydantic schemas, service layer, DI'd app
  state, CORS configured, Swagger docs.
- STR generation is real: OpenAI-backed with a seed fallback, async job stepping, and
  a proper `drafting → review → filed` lifecycle.

---

## 🔴 Critical — broken or blocks a real demo

- [x] **Frontend ↔ backend connected.** Vite proxy + `src/lib/api.js`; `App.jsx`
  polls cases + notifications; claim + notification actions call the API.
- [x] **`POST /cases/{id}/notes` fixed** — `datetime` imported in `case_service.py`.
- [~] **Per-case investigation — BACKEND done, FRONTEND pending.**
  - [x] Backend: every case now serves its own bundle (profile, timeline, graph, risk
    signals, IOB pattern, bilingual summary) from the DB via
    `GET /cases/{id}/investigation` (+ granular endpoints, no more 404s). Seeded cases
    use a generator; the primary case keeps its hand-authored showcase. Added
    `GET /session` (user/team) and made STR per-case.
  - [x] Frontend wired (Phase 2a): `Investigation.jsx` fetches
    `GET /cases/{id}/investigation` and feeds `Sidebar` (profile), `Timeline`/`Scrubber`
    (timeline), `Graph` (graph — positions by topology slot so any case renders),
    `IntelligencePanel` (signals, summary, IOB pattern, total score). Notes, confidence,
    and close/false-positive/escalate/handoff now call the API (`ActionModal`). `TopNav`
    + `CasePool` use `GET /session` for the logged-in user. **So opening any case now
    shows ITS own data.**
  - [x] Frontend Phase 2b (done): `STRDraftPanel` + `STRDrawer` now call the real STR API
    (`strGenerate` → `strJob` job-polling → `strGet` → `submit-review` → `file`) instead of
    mock STR from `constants.js`. The generation animation is driven by the backend's real
    job steps. `Investigation.jsx` passes `caseId`/`caseObj` into `STRDrawer`. Verified the
    full lifecycle end-to-end against the running backend: generate → 5 job steps →
    draft (narrative + evidenceChips + entities + complianceItems + citeSegments, all
    camelCase) → status `drafting` → `review` → `filed` (real FIU reference) → `str_status`
    persisted onto the case's investigation. `constants.js` is now only the offline
    fallback + shared time domain.
  - ⚠️ Not verified in-browser (this env has no Node) — run `npm run dev` to confirm the
    d3 timeline/graph render for a non-primary case.

## 🟠 High — core features that are stubs

- [x] **Case lifecycle completed.** `POST /cases` (ingest), `close`, `handoff`,
  `escalate` endpoints added and tested.
- [x] **Notifications have real state.** `NotificationService` implements read /
  mark-all / dismiss and auto-emits on new case / close / escalate.
- [ ] **Audit "hash chaining" isn't chained.** `audit_service.py` hashes each entry with
  a *random* token, not the previous entry's hash — append-only but not tamper-evident.
  The promised hash-chain **verification endpoint** doesn't exist.
- [x] **Real ML model DRIVES the dashboard.** `MLPipelineScoringService` loads
  `ml_pipeline`'s rule caps + fits its Isolation Forest on the real sample data.
  `score_account(bundle)` scores each case's actual behaviour (its timeline/graph) via
  noisy-OR rules ⊕ Isolation Forest. **Every case except the hand-authored primary
  showcase gets its score AND its risk-signal breakdown from the model** — at seed time,
  on seeder ingest, and via `/ml/score/case` (which now equals the shown score;
  `is_placeholder: false`). Scores show a realistic 53–91 spread.
- [x] **AI Copilot is real OpenAI — and now PER-CASE grounded.** Backend
  `POST /cases/{id}/copilot` (server-side key, no fallback → 503 if `OPENAI_API_KEY`
  missing); `AIChatPanel.jsx` calls it instead of the keyword matcher. Verified live with
  a real key: it now grounds on **each case's own** investigation bundle (was previously
  answering with the primary case's evidence for every case — fixed by injecting
  `CaseService` into `CopilotService` and reading `get_investigation(case_id)`). Confirmed
  case 4469 → AC6634821 and 4461 → AC4409127, matching ground truth. **Chat history now
  persists** per case (new `chat` SQLite table; `GET /cases/{id}/copilot/history` loaded by
  `AIChatPanel` on open; cleared by `/admin/reset`) — survives restart.
- [x] **`/health` reports the real model.** Was hardcoded to `generic-stub-v0.1.0`;
  now returns `state.ml.MODEL_VERSION` (`ml_pipeline-hybrid-v1`) so health reflects the
  actual scoring engine.
- [~] **STR is now per-case, persisted, editable, and wired end-to-end — only the "file"
  is still simulated.**
  Every case generates its own draft — non-primary cases derive evidence chips/entities
  from their own investigation bundle; the primary case keeps the hand-authored showcase
  set. Frontend STR panels drive the real API (Phase 2b).
  - [x] **Drafts persist.** New `str_drafts` SQLite table + write-through in
    `STRGenerationService` (rehydrated on startup, cleared by `/admin/reset`). Verified a
    generated + edited draft survives a full backend restart.
  - [x] **Editor is wired.** `STRDrawer` narrative is now truly editable (Edit → textarea →
    Save) via `PUT /cases/{id}/str` (`api.strUpdate`), and evidence-chip toggles persist the
    same way. Locked once `status === "filed"`.
  - Remaining gap: `file_str` still returns a **fake FIU reference** — no real FIU-IND XML
    export or digital signing.

## 🟢 Optional / polish

- [ ] **Fold the primary case (4471) into the model too.** It's currently the one
  hand-authored showcase (score 91 + rich hand-written signals). Everything else is
  model-scored. Could score it via `score_account` for full consistency — but its
  hand-authored signals (device sharing, dormancy, etc.) are richer than the model's
  3-card output, so this is a deliberate trade-off, not a bug.

## 🟡 Medium — production-readiness

- [x] **SQLite persistence + demo reset.** Cases, notifications, notes, and audit are
  persisted to `aml_shield.db` (stdlib `sqlite3`, write-through) and survive restarts.
  `POST /admin/reset` + `backend/reset_db.py` restore the clean base state between demo
  runs. STR drafts and copilot chat history are now persisted too (`str_drafts` + `chat`
  tables) and are cleared by the reset.
- [ ] **No auth/RBAC** — no JWT, no analyst/senior/compliance role checks.
- [ ] **Security checklist unchecked** — no PII encryption/redaction (PII is masked mock
  strings), no rate-limiting on the OpenAI STR path, no FIU-IND XML signing.
- [ ] **Zero tests** anywhere (frontend or backend); no CI.
- [x] **Combined run docs added** — see `README.md` (backend + seeder + frontend).

---

## Suggested critical path (for a working integrated demo)
1. Fix the `datetime` bug (`case_service.py`).
2. Add a Vite proxy + swap `constants.js` reads for API calls.
3. Generalize investigation data beyond the one case (or seed a few more).
4. Add `handoff` / `close` / `escalate` endpoints.

## Done: live seeder
- [x] **Live seeder / "make it feel alive"** — `backend/seeder.py`, a triggerable
  script that streams new cases + teammate activity into the running API. Because the
  frontend polls, the pool and notifications visibly move during a demo. Run:
  `python seeder.py` (stream) or `python seeder.py --mode burst --count 8`.
