# CLAUDE.md

Guidance for Claude Code (and similar assistants) working in **ModGent / AI Job Agent**.

## Product constraint (read first)

This is the user’s **personal** job tool. **Never implement auto-submit.** The automation fills, drafts, and pauses; the user clicks Submit and marks Applied. Do not add captcha-solving beyond `human_check.py` checkbox clicks.

## Common commands

### Development

- **Run API (primary entrypoint):**  
  `uvicorn src.api.main:app --host 127.0.0.1 --port 8000`
- **Run frontend:**  
  `cd frontend && npm run dev` → [http://localhost:5173](http://localhost:5173)
- **Ollama (local LLM):**  
  `ollama serve` — model name in code: `llama3.2` (`src/Agent/ai_generator.py`)
- **Playwright browsers (once):**  
  `playwright install msedge`
- **Tests:**  
  `pytest` — unit tests for pure helpers (scoring, dedupe, form-field matching) in `tests/`; no browser or network needed.

Restart uvicorn after Python file changes (project is often run without `--reload`).

### Obsolete commands (do not use)

- `python src/Agent/main.py` — **file does not exist**; pipeline is triggered via FastAPI (`POST /automation/discovery`).

## Architecture

### High-level flow (current)

1. **Profile** — Single SQLite row (`Profile` in `src/api/models.py`): CV path, contact, target roles, min match score, recurring answers. Edited via UI + `/profile` API.
2. **Discovery** — `src/Agent/scraper.py` (`search_all_boards`) → `pipeline.group_by_posting` → `job_scorer.score_job` → filter → `save_job`.
3. **Apply** — `application_runner.apply_to_job` (headed Edge, persistent `browser_profile/app_session`) → `form_filler.advance_application`.
4. **Review** — Blockers stored in `answers` table; frontend `DiffReviewModal`; `POST /automation/apply/{id}/answers` then **Continue**.
5. **Learn** — User-typed answers → `learned_answers` (except cover letter).

### Project structure

```
src/api/
  main.py       # FastAPI routes, background tasks
  models.py     # SQLModel tables, migrations, save_job, profile helpers
  config.py     # Paths, seeds, .env

src/Agent/
  scraper.py              # Job board discovery
  application_runner.py   # Open apply URL, advance steps, never Submit
  form_filler.py          # DOM/iframe fill, blockers, cover letter, dropdowns
  session_registry.py     # Live Playwright session per job_id
  parse_cv.py / read_cv.py
  job_scorer.py / pipeline.py
  ai_generator.py         # Ollama client
  human_check.py          # Cloudflare checkbox helper

frontend/src/
  pages/MainLayout.tsx    # Command Center, Hunt, Lab, Ledger
  hooks/useAgent.ts
  components/ui/DiffReviewModal.tsx

jobs.db                 # Local SQLite (gitignored)
browser_profile/        # Edge user data (gitignored)
data/cv/                # Uploaded CVs (gitignored)
```

`scripts/lessons/` (tutorials) and `scripts/experiments/` (manual Playwright probes) are not part of the shipped app.

## Design tokens (UI)

- Accent `#7C3AED`, hover `#6D28D9`, soft `#A78BFA`
- Inter + JetBrains Mono; theme key `jobagent-theme` in localStorage
- See `frontend/src/styles/globals.css`

## Handoff doc

For deeper context (state machine, API table, regression notes), read **[AGENTS.md](./AGENTS.md)**.
