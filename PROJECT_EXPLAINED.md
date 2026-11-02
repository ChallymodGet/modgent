# Project explanation: ModGent (AI Job Agent)

## Purpose

ModGent reduces repetitive job-hunt work while keeping the candidate in control of every submission. It discovers roles, scores fit against a real CV, opens employer application sites in a visible browser, pre-fills and drafts content, and **stops before Submit** so the user can review and send applications themselves.

## System components

### 1. Command Center UI (React + Vite)

A single-page app with job-centric views: dashboard actions, full job list, profile/CV settings, and an activity log fed by backend tasks. The review experience centers on **DiffReviewModal**: site-sourced dropdown/checkbox options, visible autofill drafts, and a dedicated cover-letter flow (draft first, upload after approval).

### 2. API layer (FastAPI)

Exposes jobs, profile, discovery, and apply endpoints. Long work runs in **BackgroundTasks** with pollable `Task` rows (status, result, JSON `progress`). CORS is open for local dev (`localhost:5173` → `127.0.0.1:8000`).

### 3. Data layer (SQLite + SQLModel)

- **jobs** — listings, match score, status lifecycle  
- **profile** — one row for candidate config and CV metadata  
- **tasks** — discovery/apply runs  
- **answers** — per-job blockers (draft/final, choices, kind)  
- **learned_answers** — cross-job reuse for repeated questions (not cover letters)

Schema evolves via lightweight `ALTER TABLE` migrations on startup for older local databases.

### 4. Automation (Playwright + Edge)

- **Discovery** uses a search-oriented persistent profile; scraping is async across boards.  
- **Apply** uses a separate persistent profile, **always headed**, so the user sees the same form the agent fills.  
- **Session registry** keeps the browser open between Apply, answer review, and Continue.  
- **ATS awareness** — Many employers embed Greenhouse/Lever in iframes; logic scopes locators to the embed and handles cookie banners and Indeed external-apply redirects.

### 5. Intelligence (local Ollama)

Open-ended answers and cover letters call **Ollama** on the machine (`llama3.2`). No cloud API key is required. If Ollama is down, fallbacks are intentionally conservative so the user is prompted to review rather than sending boilerplate or CV headers as a “letter.”

## Current maturity

| Area | Status |
|------|--------|
| API + UI wired for discovery, apply, profile | Done |
| Match scoring + dedupe on discovery | Done |
| Human review modal + learned answers | Done |
| Greenhouse-style embeds + Indeed handoff | Worked in development; site changes break often |
| Automated test suite in repo | Not shipped |
| Production deploy / auth | Out of scope (local tool) |

## Operational notes for maintainers

- Only one apply automation should use `browser_profile/app_session` at a time.  
- Personal artifacts stay on disk: `jobs.db`, `data/`, `browser_profile/`.  
- Public source is on GitHub as **modgent**; clones need fresh local profile + CV upload.  

For file-level maps and agent rules, see **[AGENTS.md](./AGENTS.md)** and **[README.md](./README.md)**.
