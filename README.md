# ModGent (AI Job Agent)

ModGent is a full-stack job discovery and **assisted** application tool. It scrapes boards, scores listings against your CV, opens real employer application forms in Microsoft Edge, pre-fills what it can, drafts open-ended answers and cover letters with a **local** LLM (Ollama), and stops for your review. **It never clicks Submit** — you submit and mark the job Applied in the UI.

Public repo: [github.com/ChallymodGet/modgent](https://github.com/ChallymodGet/modgent)

## Prerequisites

- **Python 3.11+** (project has been run on 3.14)
- **Node.js 20+** for the frontend
- **Microsoft Edge** (Playwright uses `channel="msedge"`)
- **Ollama** with `llama3.2` (or `llama3.2:latest`) for cover letters and open-ended answers  
  Run `ollama serve` before apply flows that need AI text.

First-time setup:

```bash
python -m venv .venv
.venv\Scripts\activate          # Windows
pip install -r requirements.txt
playwright install msedge

cd frontend
npm install
```

Optional: copy `.env` from `.env.example` if you add one later; defaults live in `src/api/config.py` and are overridden by the **Profile** row in SQLite after first launch.

## Run locally

**Backend** (from repo root, venv active):

```bash
uvicorn src.api.main:app --host 127.0.0.1 --port 8000
```

Restart uvicorn after Python changes (no `--reload` in production use).

**Frontend**:

```bash
cd frontend
npm run dev
```

Open [http://localhost:5173](http://localhost:5173). API base URL is hardcoded to [http://127.0.0.1:8000](http://127.0.0.1:8000) in `frontend/src/utils/api.ts`.

Interactive API docs: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)

## Typical workflow

1. **Profile (The Lab)** — Upload a PDF CV, set name, contact, target roles (comma-separated), search location, minimum match score, and recurring answers (work authorization, sponsorship, etc.).
2. **Discovery** — Trigger a scan from the UI. The backend scrapes LinkedIn, Indeed, and Wellfound (see `src/Agent/scraper.py`), dedupes cross-listed postings, scores against CV skills, and saves jobs that meet `min_match_score`.
3. **Apply** — Opens a **headed** Edge window with profile `browser_profile/app_session`. For Indeed external apply, the runner waits out interstitials and loads the employer ATS (Greenhouse, Lever, etc.).
4. **Review** — When required fields or AI drafts need you, status becomes **Needs you**. Use the diff review modal: edit drafts, pick dropdown/checkbox options from the **site’s** list, approve the cover letter (upload happens after you save). **Cover letter answers are not stored as learned answers.**
5. **Continue** — Reuses the same browser session via `session_registry` until the form reaches a review/submit step or pauses again.
6. **Submit manually** — Click Submit in the browser yourself, then **Mark applied** in the UI (`PATCH /jobs/{id}?status=Applied`), which harvests fields you typed and closes the session.

## Architecture (short)

| Layer | Location | Role |
|--------|-----------|------|
| UI | `frontend/` | React 18, Vite 8, Tailwind v4, Command Center / Hunt / Lab / Ledger |
| API | `src/api/main.py` | FastAPI, background tasks for discovery and apply |
| Data | `src/api/models.py` | SQLModel + SQLite (`jobs.db`), Profile, jobs, tasks, answers, learned_answers |
| Automation | `src/Agent/` | Playwright apply runner, form filler, scraper, scoring, CV parse |
| AI | `src/Agent/ai_generator.py` | Ollama `http://localhost:11434`, model `llama3.2` |

**Browser profiles** (gitignored):

- `browser_profile/search_session` — discovery (mostly headless; Indeed may open headed for Cloudflare).
- `browser_profile/app_session` — apply only; only one process can use a profile at a time.

**Personal data** (gitignored):

- `jobs.db`, `data/cv/`, `data/cover_letters/`, `.env`

## Design system

- Accent `#7C3AED`, hover `#6D28D9`, soft `#A78BFA`
- Fonts: Inter (UI), JetBrains Mono (code/log)
- Theme: light default; dark via `localStorage` key `jobagent-theme` (`frontend/src/hooks/useTheme.ts`)
- Tokens in `frontend/src/styles/globals.css`

## Job statuses

`Not Reviewed`, `Needs you`, `Pending Review`, `Ready to Submit`, `Applied`, `Interviewing`, `Offer`, `Ghosted` — see `JobCard` / `StatusBadge` for UI grouping.

## What works well

- CV-based match scoring and deduped discovery before apply.
- Human-in-the-loop review modal (draft vs your edit, site dropdown options, multi-select checkboxes).
- Persistent apply sessions so Continue does not reopen a cold browser.
- Greenhouse/Lever embed handling (iframe scope, cookie banners, no parent scroll-to-bottom).

## Known pain points

- **Ollama offline** — Cover letter / open-ended text falls back to weaker heuristics; keep `ollama serve` running.
- **Indeed / Cloudflare / cookie banners** — May require manual checks; `human_check.py` only clicks visible challenge checkboxes (no token forging).
- **ATS quirks** — React-select comboboxes need field-specific option reads; phone-country lists must not attach to unrelated questions (see `form_filler.py`).
- **Single profile lock** — Close stray Edge windows before Apply/Continue if you see “browser session already in use”.
- **Legacy / noise** — `src/Lesson/` are learning scripts; root `main.py` is a stub. There is no `src/Agent/main.py`; orchestration is API-driven.

## For AI assistants continuing this repo

Read **[AGENTS.md](./AGENTS.md)** first — constraints, file map, apply state machine, and safe-change guidelines. **[CLAUDE.md](./CLAUDE.md)** mirrors commands and structure for Claude Code.

## License

Not specified in repo; treat as private author project unless a license file is added.
