# ModGent

An AI job agent that finds roles, grades how well each one fits you, pre-fills your saved application details, and stops so you can review and submit. You never apply to roles you're not qualified for by accident.

## The problem
Applying widely wastes time, and most of it goes to roles that were never a fit. ModGent scores every listing against your profile first, so your effort goes only to roles worth applying for.

## How it works
1. **Profile:** parses your PDF CV and ranks your skills.
2. **Discover:** scrapes multiple job boards asynchronously with Playwright.
3. **Grade:** gives each job a semantic match score against your profile.
4. **Tailor and pre-fill:** an LLM (Llama 3.2) tailors your application, and your saved fields are filled in.
5. **Review:** a diff review screen shows what the agent changed, and you approve it. The agent waits for you to submit.

## Design
I designed the product and the UI myself, then built it with AI coding tools (Claude Code and Cursor).
- **Design system:** tokens for colour, typography and a strict 8px spacing unit, in an "engineering-led monochrome" style inspired by Linear and Vercel.
- **Component library (React):** atoms (Button, StatusBadge, Input, ConfidenceIndicator), molecules (JobCard, AgentLogEntry) and organisms (ApplicationStepper, DiffReviewModal).
- **Information architecture:** four job-centred views:
  - **Command Center:** priority actions.
  - **The Hunt:** the master job board with filters.
  - **The Lab:** your profile and candidate intelligence.
  - **The Ledger:** a transparent audit trail of everything the agent did.

## Stack
- **Backend:** Python, Playwright, SQLModel, SQLite
- **Frontend:** TypeScript, React
- **AI:** Llama 3.2 for application tailoring

## Status
Backend engine and UI are built. [One line on where wiring or API integration stands today.]

## Run it locally
1. `pip install -r requirements.txt`
2. backend: uvicorn src.api.main:app --host 127.0.0.1 --port 8000
3. cd frontend, then npm install, then npm run dev

## What worked and what didn't
- **Worked:** Scoring each role against the CV and only keeping the ones above the match threshold, and the review screen, which shows the drafted answers and cover letter so you approve them and click Submit yourself.
- **Didn't:** Indeed and Greenhouse often blocked or hid the form (Cloudflare, the cookie banner, the application sitting in an iframe), and the cover letter fell back to a raw CV paste whenever the local model was not running.

## Screenshots
[Add two or three screenshots of Command Center, The Hunt and the diff review screen]
