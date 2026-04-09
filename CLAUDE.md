# LLM-COUNSEL — Claude Agent Guide

This document provides context for AI agents working with the LLM-COUNSEL legal
deliberation system.

## System Overview

LLM-COUNSEL orchestrates multiple frontier LLMs, each playing a named legal
persona, through a 3-stage deliberation process that produces a final strategy
memorandum. The architecture separates **roles** (personas) from **models**
(OpenRouter slugs) so the same persona can be re-cast onto a different model
without touching prompt logic.

## Architecture

### Three-Stage Deliberation

```
Legal Question
    │
    ▼
Stage 1 — Initial Analyses     (parallel calls, one per persona)
    │
    ▼
Stage 2 — Peer Ranking         (blind, each persona ranks the anonymized set)
    │
    ▼
Stage 3 — Lead Counsel Memo    (synthesizes analyses + aggregate ranking)
```

### Active Persona Team

Defined in `backend/config.py` as `COUNSEL_TEAM`:

| Role                    | Display Name              | Model                            |
|-------------------------|---------------------------|----------------------------------|
| `plaintiff_strategist`  | Plaintiff's Strategist    | `x-ai/grok-4.20`                 |
| `defense_analyst`       | Defense Analyst           | `anthropic/claude-opus-4.6`      |
| `procedural_specialist` | Procedural Specialist     | `openai/gpt-5.4`                 |
| `evidence_counsel`      | Evidence Counsel          | `google/gemini-3.1-pro-preview`  |

**Lead Counsel:** `google/gemini-3.1-pro-preview` (longest context in the
lineup, different family from `defense_analyst` for diversity).

Four additional personas — `appellate_consultant`, `settlement_strategist`,
`trial_tactician`, `regulatory_specialist` — are registered in
`backend/prompts/personas.py` but not active by default. Swap them in by
editing `COUNSEL_TEAM`.

### Degraded Modes

- **Some Stage 1 models fail:** Deliberation continues with the remaining
  personas. Stage 2 only runs evaluators whose Stage 1 succeeded.
- **All Stage 1 models fail:** `AllModelsFailedError` → API returns 502.
- **Stage 2 parsing fails:** `aggregate_rankings` is empty; Stage 3 still runs
  and is told to proceed without the distilled ranking signal.
- **Lead Counsel fails:** Returned in-band as `stage3.error`; Stage 1 + Stage 2
  work is still persisted and visible to the user.

## Development Commands

### Start the app

```bash
# Both servers via the helper script
./start.sh

# Or separately:
# Backend (port 8001)
source .venv/bin/activate
uvicorn backend.main:app --reload --port 8001

# Frontend (port 5173)
cd frontend && npm run dev
```

### Tests

```bash
source .venv/bin/activate
python -m pytest tests/ -v
```

39 tests across 5 files, all hermetic (no network required):
- `tests/test_personas.py` — registry shape + active team
- `tests/test_ranking_parser.py` — fail-closed semantics, ordinal validation
- `tests/test_storage.py` — round-trip + concurrent writes (threads AND processes)
- `tests/test_counsel_orchestration.py` — mocked end-to-end, including partial-failure paths
- `tests/test_openrouter.py` — timeout/HTTP/malformed-JSON error mapping

### Lint

```bash
ruff check backend/ tests/
```

## API Endpoints

| Method | Path                              | Purpose                                   |
|--------|-----------------------------------|-------------------------------------------|
| GET    | `/`                               | Health check                              |
| GET    | `/api/config/team`                | Active team metadata (for welcome screen) |
| GET    | `/api/matters`                    | List matters                              |
| POST   | `/api/matters`                    | Create matter                             |
| GET    | `/api/matters/{id}`               | Get matter with full history              |
| DELETE | `/api/matters/{id}`               | Delete matter                             |
| POST   | `/api/matters/{id}/message`       | Submit question → full 3-stage deliberation |

## Key Files

### Backend

| File                             | Purpose                                      |
|----------------------------------|----------------------------------------------|
| `backend/main.py`                | FastAPI server + startup validation          |
| `backend/config.py`              | `COUNSEL_TEAM`, `LEAD_COUNSEL_MODEL`, env    |
| `backend/counsel.py`             | 3-stage orchestration                        |
| `backend/openrouter.py`          | Async OpenRouter client (typed errors)       |
| `backend/storage.py`             | JSON storage with fcntl lockfiles + atomic writes |
| `backend/errors.py`              | Typed exception hierarchy                    |
| `backend/prompts/personas.py`    | 8 persona definitions (4 active)             |
| `backend/prompts/stage1.py`      | `build_stage1_prompt()`                      |
| `backend/prompts/stage2.py`      | `build_stage2_prompt()` + `parse_ranking()`  |
| `backend/prompts/stage3.py`      | `build_stage3_prompt()`                      |

### Frontend

| File                                         | Purpose                                |
|----------------------------------------------|----------------------------------------|
| `frontend/src/App.jsx`                       | Main app + welcome screen with team panel |
| `frontend/src/api.js`                        | API client (uses Vite proxy)           |
| `frontend/src/components/Sidebar.jsx`        | Matter list navigation                 |
| `frontend/src/components/MatterInterface.jsx`| Per-message tabs + input form          |
| `frontend/src/components/Stage1Display.jsx`  | Per-persona analysis viewer            |
| `frontend/src/components/Stage2Display.jsx`  | Aggregate rankings + individual evaluations |
| `frontend/src/components/Stage3Display.jsx`  | Letterhead-style Lead Counsel memo     |

## Data Model

Matters stored as JSON in `data/conversations/`:

```json
{
  "id": "matter_abc123",
  "created_at": "2026-04-09T12:00:00+00:00",
  "matter_name": "Smith v. Acme",
  "practice_area": "employment",
  "jurisdiction": "federal",
  "messages": [
    { "role": "user", "content": "...", "context": "..." },
    {
      "role": "assistant",
      "stage1": { "plaintiff_strategist": {...}, ... },
      "stage2": {
        "assessments": { "plaintiff_strategist": {...}, ... },
        "label_mapping": { "A": "plaintiff_strategist", ... },
        "aggregate_rankings": [ {...}, ... ]
      },
      "stage3": { "model": "...", "content": "...", "error": null }
    }
  ]
}
```

Each matter has a sentinel lockfile `.{matter_id}.lock` in the same directory;
all RMW operations serialize on it via `fcntl.flock`. Writes are atomic via
temp-file + `os.replace()`.

## Adding a New Persona

1. Add a `Persona` entry to `LEGAL_PERSONAS` in `backend/prompts/personas.py`
2. Add the role to `COUNSEL_TEAM` in `backend/config.py` if you want it active
3. Run tests — `test_active_team_uses_registered_personas` will catch typos

## Modifying Deliberation Behavior

- **Stage 1 prompts:** `backend/prompts/stage1.py::build_stage1_prompt`
- **Stage 2 prompts + parser:** `backend/prompts/stage2.py`
- **Stage 3 synthesis:** `backend/prompts/stage3.py::build_stage3_prompt`
- **Self-vote exclusion / aggregation:** `backend/counsel.py::aggregate_rankings`

## Environment Variables

```bash
OPENROUTER_API_KEY=sk-or-v1-...     # Required
API_HOST=127.0.0.1                  # Optional; default bind
API_PORT=8001                       # Optional
DATA_DIR=data/conversations         # Optional
MODEL_REQUEST_TIMEOUT=180.0         # Optional; per-call timeout in seconds
```

## Quick Reference

```bash
# Start app
./start.sh

# API docs
open http://localhost:8001/docs

# Frontend
open http://localhost:5173

# Run tests
source .venv/bin/activate && python -m pytest tests/ -v
```
