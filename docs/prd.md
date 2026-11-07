# ModGent — Product Requirements Document

| | |
|---|---|
| **Product** | ModGent (AI Job Agent) |
| **Owner** | Charles Ifeoluwa Onofuevure |
| **Document status** | Living document, reverse-engineered from the codebase (Nov 2026), updated for the `fix/prd-gaps` changes |
| **Related** | [Product definition](./product-definition.md) · [Domain model](./domain-model.md) · [AGENTS.md](../AGENTS.md) |

Requirement status key: **Shipped** (in code and working), **Partial** (in code with known limits), **Gap** (not built).

## 1. Summary

ModGent automates the repetitive parts of a job search (finding listings, judging fit, filling application forms) while keeping the candidate in control of every submission. This PRD records what the product must do, what it does today, and where it falls short.

## 2. Goals and non-goals

### Goals

- **G1.** Cut time spent on poor-fit listings by scoring every listing against the candidate's CV before any application work.
- **G2.** Cut repetitive typing on application forms by filling known fields and reusing past answers.
- **G3.** Keep every application reviewed and submitted by the candidate.
- **G4.** Keep candidate data on the candidate's machine.

### Non-goals

- Auto-submitting applications, in any mode.
- Bypassing captchas, Cloudflare or bot detection.
- Multi-user accounts, authentication, or cloud deployment.
- Supporting every ATS; the target is the common ones (Greenhouse, Lever, Indeed-hosted forms).

## 3. Users

| Persona | Description | Primary needs |
|---|---|---|
| **Focused job seeker** (primary) | One person applying to skilled roles, a few to tens per week, who reviews everything they send | Fit filtering, no retyping, full review, privacy |
| **Maintainer** (secondary) | The same person, or an AI coding assistant, extending the tool | Clear rules, tests, a predictable apply state machine |

## 4. User journeys

### J1. First-time setup
1. User starts the API and UI locally, and runs Ollama.
2. In **The Lab**, uploads a PDF CV, enters contact details, target roles (comma-separated), search location, minimum match score, and recurring answers.
3. Profile is saved to the local database.

### J2. Discover jobs
1. User clicks **Scan** in Command Center.
2. Progress shows each board (waiting → opening → reading → done) and a running listing count.
3. When finished, new qualifying jobs appear as **Not Reviewed**, ordered by match score; the Ledger records a summary ("Scraped N, M unique, K met threshold, saved X new").

### J3. Apply with review
1. User clicks **Apply** on a job. A visible Edge window opens on the listing and follows through to the employer form.
2. The agent uploads the CV, fills known fields, drafts open-ended answers, and moves through Next steps.
3. If required fields remain, the job becomes **Needs you** and the review window opens automatically, listing each blocker with the site's own options.
4. User edits or approves answers and saves. Answers are typed into the same tab; answers the user changed are remembered.
5. User clicks **Continue**; the agent resumes. Steps 3–5 repeat as needed.
6. On reaching Review/Submit, the job becomes **Pending Review**. The agent stops.
7. User checks the form, clicks Submit in the browser, then clicks **Mark applied**. Fields they typed by hand are harvested as learned answers and the browser session closes.

## 5. Functional requirements

### 5.1 Profile and CV

| ID | Requirement | Status |
|---|---|---|
| P-1 | Store a single candidate profile: name, email, phone, LinkedIn, portfolio, location, country, search location, target roles, minimum match score, recurring answers. | Shipped |
| P-2 | Accept PDF CV upload only; store it under a generated filename and remember the original filename for display and upload to employers. Delete the previous CV file on replacement. | Shipped |
| P-3 | Derive core skills and a candidate summary from the CV text for scoring and drafting. | Shipped |
| P-4 | Seed the profile from configuration defaults on first run; after that the database is the source of truth. | Shipped |
| P-5 | List and delete learned answers from The Lab. | Shipped |
| P-6 | Validate profile fields (email format, score 0–100). | Gap |

### 5.2 Discovery

| ID | Requirement | Status |
|---|---|---|
| D-1 | Refuse to run without a CV and at least one target role, with a clear message. | Shipped |
| D-2 | Search LinkedIn, Indeed and Wellfound at the same time for the target roles and search location, up to 15 listings per board. One board failing must not lose the others' results. | Partial — boards run in parallel, each with its own browser profile, and Wellfound browses one role page per target role; LinkedIn and Indeed still receive all target roles as one combined keyword string |
| D-3 | Report live progress per board (phase, count, message) through the task. | Shipped |
| D-4 | Detect sign-in walls and Cloudflare challenges; click a visible challenge checkbox only, otherwise report the board as blocked. | Shipped |
| D-5 | Merge postings that share company, title and description. | Partial — exact-match only; the same job with different description text is not merged |
| D-6 | Score each unique listing 0–100 (see 5.3) and save only those at or above the profile's minimum score. | Shipped |
| D-7 | Never overwrite a job that already exists (same job ID), so its status survives rescans. | Shipped |
| D-8 | Job IDs are unique across boards. | Gap — IDs are board-native (LinkedIn number, Indeed `jk`, Wellfound ID) with no board prefix, so a collision between boards would silently drop the second job |

### 5.3 Scoring

Current formula (`src/Agent/job_scorer.py`). All matching is whole-word and case-insensitive.

| Component | Weight | Rule |
|---|---|---|
| Title match | 30 | Any target role appears in the job title |
| Skill coverage | 30 | Share of CV core skills named in the description |
| Core strength | 25 | The same matches weighted by each skill's rank in the CV (most-used skill weighs most), so matching the candidate's strongest skills scores higher |
| Role relevance | 15 | Any target role appears in the description |

Grouped skills such as "AI Tools (ChatGPT, Claude)" match if any member appears. The score is keyword-based, not semantic; the README says so.

| ID | Requirement | Status |
|---|---|---|
| S-1 | Score deterministically from title, description, target roles and CV skills. | Shipped |
| S-2 | Skill components measure different things. | Shipped — coverage counts matches; core strength weights them by CV rank |
| S-3 | Match whole words, not substrings (e.g. "UI" should not match "build"). | Shipped |
| S-4 | Explain a score to the user (which roles/skills matched). | Gap |

### 5.4 Job tracking

| ID | Requirement | Status |
|---|---|---|
| T-1 | Show jobs grouped by status in priority order: Needs you, Pending Review, Ready to Submit, Not Reviewed, Interviewing, Offer, Applied, Ghosted. | Shipped |
| T-2 | Offer Continue / Apply / Mark applied on jobs waiting on the user; Apply on other unapplied jobs. | Shipped |
| T-3 | Let the user move a job on after applying: Applied → Interviewing or Ghosted; Interviewing → Offer or Ghosted; Ghosted → Interviewing. | Shipped |
| T-4 | Accept only known status values. | Shipped — `PATCH /jobs/{id}` returns 400 for unknown statuses |
| T-5 | Let the user dismiss or hide a job they won't apply to. | Gap |

### 5.5 Assisted apply

| ID | Requirement | Status |
|---|---|---|
| A-1 | Open the job URL in a **visible** Edge window using a dedicated apply browser profile, separate from discovery. | Shipped |
| A-2 | Follow Indeed's external-apply redirect and wait out interstitial pages before filling. | Shipped |
| A-3 | Find the form inside embedded ATS iframes (Greenhouse, Lever) and dismiss cookie banners. | Shipped |
| A-4 | Upload the CV using the candidate's original filename. | Shipped |
| A-5 | Fill fields from contact details, then recurring answers, then learned answers, in that priority. | Shipped |
| A-6 | Never fill protected demographic or EEO questions. | Shipped |
| A-7 | Read options for dropdowns, radios and checkboxes from the field itself; ignore phone-country lists attached to unrelated questions. | Shipped |
| A-8 | Advance through Next/Continue up to 8 steps; click Review if present. | Shipped |
| A-9 | **Never click Submit**, "Submit application" or a final "Apply Now". Stop and mark the job Pending Review. | Shipped (hard invariant) |
| A-10 | When required fields remain, store them as blockers, mark the job Needs you, and end the task with outcome `needs_you`. | Shipped |
| A-11 | Keep the browser open between Apply, review and Continue for the same job. | Shipped — in memory only; lost if the API restarts |
| A-12 | If the session is gone when answers are saved, keep the answers, mark the job Ready to Submit and tell the user. | Shipped |
| A-13 | Explain a busy browser profile ("window already open") in plain language. | Shipped |
| A-14 | Avoid mis-filling fields whose label merely contains a keyword. | Partial — known bugs: "personal statement" gets the location; any question containing "experience" gets years of experience (tracked by `xfail` tests) |
| A-15 | If the user closed the application window, Apply/Continue reopens the form and says so; saving answers or marking Applied falls back cleanly instead of failing. | Shipped |

### 5.6 Review and drafting

| ID | Requirement | Status |
|---|---|---|
| R-1 | Draft answers to open-ended questions with the local model, using the job description and CV summary. | Shipped |
| R-2 | Show each blocker with its draft, the site's options (chips or select), and whether the draft came from a remembered answer. | Shipped |
| R-3 | Support multi-select checkbox questions with newline-separated answers. | Shipped |
| R-4 | Type approved answers into the live form. | Shipped |
| R-5 | Remember an answer only when the user typed or changed it; never remember cover letters or protected questions. | Shipped |
| R-6 | Harvest fields the user typed directly in the browser when they click Continue or Mark applied. | Shipped |
| R-7 | Draft a cover letter as a PDF when the form asks for one; show it for approval before uploading. | Shipped |
| R-8 | Reject drafts that look like a pasted CV header (contact details, pipes, "summary" + "linkedin"). | Shipped |
| R-9 | Tell the user when the local model is unavailable instead of silently falling back. | Partial — logged to the server console only |

### 5.7 Activity log

| ID | Requirement | Status |
|---|---|---|
| L-1 | Record every discovery and apply run with status, phase and a human-readable result. | Shipped (stored in the `tasks` table) |
| L-2 | Show runs in The Ledger with success/error styling, including runs from earlier sessions. | Shipped — loaded from `GET /automation/tasks`; runs still in progress resume polling after a refresh |
| L-3 | A run interrupted by a server restart must not show as running forever. | Shipped — marked failed at startup |

## 6. Non-functional requirements

| ID | Requirement | Status |
|---|---|---|
| N-1 | **Privacy:** CVs, database, browser profiles and cover letters stay on disk and are gitignored; no cloud LLM calls. | Shipped |
| N-2 | **Single-instance safety:** only one apply automation uses the apply browser profile at a time; discovery uses its own profile. | Shipped |
| N-3 | **Responsiveness:** CV parsing runs off the event loop; long work runs as background tasks the UI polls every 1.5 s. | Shipped |
| N-4 | **Schema evolution:** older local databases gain new columns on startup without data loss. | Shipped (hand-written `ALTER TABLE` steps) |
| N-5 | **Testability:** pure logic (scoring, dedupe, field matching) has unit tests runnable without a browser. | Shipped (48 tests) |
| N-6 | **Resilience:** an API restart should not lose the user's place in an application. | Gap |
| N-7 | **Local-only exposure:** the API listens on 127.0.0.1 with no authentication. | Shipped — must not be exposed on a network |

## 7. Constraints and dependencies

- Microsoft Edge (Playwright `msedge` channel), Python 3.11+, Node 20+.
- Ollama running `llama3.2` locally for drafts and cover letters.
- Job board and ATS markup changes frequently; selectors break without notice.
- LinkedIn and Indeed actively challenge automation; some runs need the user to clear a check by hand.
- On managed Windows machines, `.venv` launcher executables may be blocked; run tools with `python -m`.

## 8. Success metrics

Definitions to instrument; none are reported by the app today.

| Metric | Definition | Supports |
|---|---|---|
| Apply-through rate | Jobs moved to Applied ÷ jobs saved by discovery | G1 |
| Autofill rate | Fields filled without user input ÷ fields seen on forms | G2 |
| Draft acceptance | AI drafts approved unchanged or lightly edited ÷ drafts shown | G2, G3 |
| Run reliability | Apply tasks ending in `review` or `needs_you` ÷ apply tasks started | G2 |
| Agent submissions | Applications submitted by the agent | G3 — must always be 0 |

## 9. Risks

| Risk | Impact | Mitigation |
|---|---|---|
| Board or ATS markup changes | Discovery or filling silently degrades | Manual experiments in `scripts/experiments/`; add smoke checks per board |
| Account flagged for automation | User loses access to a job board | Visible browser, low volume, no stealth tooling, user clears challenges |
| Wrong value typed into a field | Embarrassing or incorrect application | Review before submit, protected-field rule, unit tests for field matching |
| Local model offline | Weak or missing drafts | Dump detection; surface the outage in the UI (R-9) |
| API restart mid-application | Session lost; user must reopen | Answers persist; Ready to Submit status (A-12); session recovery (N-6) |

## 10. Prioritised backlog

| Priority | Item | Requirement |
|---|---|---|
| P1 | Fix keyword false positives in field matching ("statement", "experience") | A-14 |
| P1 | Dismiss or hide a job | T-5 |
| P2 | Prefix job IDs with the board | D-8 |
| P2 | Show why a job scored as it did | S-4 |
| P2 | Show "local model offline" in the UI | R-9 |
| P2 | Search LinkedIn and Indeed once per target role instead of one combined query | D-2 |
| P3 | Fuzzy duplicate detection | D-5 |
| P3 | Instrument success metrics | §8 |

Done in `fix/prd-gaps`: Ledger history (L-2), status actions and validation (T-3, T-4), Wellfound roles and parallel boards (D-2), distinct whole-word scoring (S-2, S-3), closed-window recovery (A-15).

## 11. Open questions

1. Should the scorer move to embeddings (true semantic match), or stay keyword-based with better weighting and explanations?
2. Is a "dismissed" status needed, or is a filter on Not Reviewed enough?
3. Should learned answers be scoped per role type (designer vs. engineer applications)?
4. Is session recovery after an API restart worth the complexity, given Ready to Submit already preserves answers?
