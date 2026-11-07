# ModGent — Product Definition

| | |
|---|---|
| **Product** | ModGent (AI Job Agent) |
| **Type** | Local, single-user desktop web app (React UI + FastAPI service + Playwright browser automation) |
| **Owner** | Charles Ifeoluwa Onofuevure |
| **Status** | Working prototype, used personally; not deployed or multi-user |
| **Related** | [PRD](./prd.md) · [Domain model](./domain-model.md) · [AGENTS.md](../AGENTS.md) |

## 1. One-line definition

ModGent is a job-search co-pilot that finds roles, scores how well each one fits your CV, pre-fills the employer's application form in a visible browser, and stops so **you** review and click Submit.

## 2. The problem

Applying for jobs at volume has two kinds of waste:

1. **Wasted effort on bad fits.** Most listings returned by a board search are only loosely related to the candidate. Reading each one to decide is slow, and applying to poor fits lowers response rates.
2. **Wasted effort on repetition.** Every employer's application tracking system (ATS) asks for the same name, email, LinkedIn, work authorization, sponsorship, salary, and "how did you hear about us", in slightly different form controls. Typing these again for every application is tedious and error-prone.

Fully automatic "spray and pray" tools try to fix both by auto-submitting at scale. That trades one problem for worse ones: low-quality applications sent in the candidate's name, answers the candidate never saw, and accounts flagged by job boards.

## 3. Who it is for

**Primary user: an individual job seeker applying to skilled roles** (the current configuration targets Product Designer roles) who:

- applies to tens of roles a week across LinkedIn, Indeed and Wellfound;
- cares about application quality and wants to see every answer before it is sent;
- is comfortable running a local app (Python, Node, Ollama) on their own machine.

Not for: recruiters, agencies, or anyone wanting unattended mass applications.

## 4. Value proposition

| For the job seeker who… | ModGent… | Unlike… |
|---|---|---|
| wastes time on poor-fit listings | scores every listing against their actual CV and only keeps ones above their chosen threshold | reading every search result by hand |
| retypes the same details on every ATS form | fills known fields, reuses answers they gave before, and drafts open-ended answers and cover letters | copying and pasting from a notes file |
| doesn't want a bot speaking for them | pauses for review, shows drafts next to their edits, and **never clicks Submit** | auto-apply bots that submit without review |
| worries about sharing personal data | runs locally: SQLite on disk, local LLM via Ollama, no cloud API keys | SaaS tools that upload CVs and answers |

## 5. Product principles

These are product rules, not preferences. Changes that break them are out of scope.

1. **The human submits.** The agent fills, drafts and pauses. It never clicks Submit or an equivalent final-step button. The user marks a job Applied themselves.
2. **Show your work.** Every AI draft and every answer the agent could not fill is surfaced for review before it reaches the form.
3. **Quality over volume.** Filtering by fit happens before any application effort is spent.
4. **Learn once, reuse forever.** An answer the user types once is remembered for the same question on future applications (cover letters excepted; they are per-job).
5. **Local and private by default.** Candidate data, CVs, browser sessions and the job database stay on the user's machine.
6. **No evasion.** No captcha solving or stealth tooling beyond clicking a visible "I'm human" checkbox. If a site blocks automation, the user takes over.
7. **Never fill protected questions.** Demographic and EEO questions (race, gender, disability, veteran status, etc.) are left for the user.

## 6. Core capabilities

| Capability | What the user gets |
|---|---|
| **Profile ("The Lab")** | Upload a PDF CV; set contact details, target roles, search location, minimum match score and standard logistics answers. Review and delete remembered answers. |
| **Discovery** | One click scans LinkedIn, Indeed and Wellfound, merges duplicates, scores each listing against CV skills and target roles, and saves the ones above the threshold. Live progress per board. |
| **Job board ("The Hunt" / Command Center)** | Jobs grouped by status, ordered by what needs attention first, with match score and one-click actions. |
| **Assisted apply** | Opens the employer's real form in Edge, follows Indeed's redirect to the company ATS, uploads the CV, fills known fields, moves through Next steps, and stops at Review/Submit. |
| **Review** | A side-by-side review window shows AI drafts and required blanks, using the site's own dropdown and checkbox options. Approved answers are typed into the same open browser tab. |
| **Cover letters** | Drafted per job by the local model from the CV and job description, saved as a PDF, and uploaded only after the user approves it. |
| **Activity ("The Ledger")** | A log of discovery and apply runs with their outcome and the next action needed. |

## 7. Scope

**In scope:** discovery on three boards, CV-based scoring, assisted form filling on common ATSs (Greenhouse, Lever, Indeed-hosted), human review, learned answers, cover letter drafting, status tracking through to Applied.

**Out of scope (by design):** auto-submit, captcha or bot-detection bypass, multi-user accounts, cloud hosting, emailing employers, scheduling interviews.

## 8. How we know it works

| Outcome | Signal |
|---|---|
| Less time on poor fits | Share of saved jobs the user chooses to apply to (higher is better) |
| Less retyping | Share of form fields filled without user input; growth of learned answers over time |
| Trustworthy drafts | Share of AI drafts approved unchanged or with light edits |
| Reliable automation | Share of apply runs that reach Review or a clear "needs you" pause, versus failing |
| Safety | Zero applications submitted by the agent (a hard invariant, not a target) |

These are definitions to instrument; the app does not yet report them. See the [PRD](./prd.md) for the gaps.

## 9. Product vocabulary

| Term | Meaning |
|---|---|
| **Match score** | 0–100 fit between a listing and the candidate's target roles and CV skills |
| **Blocker** | A required form field the agent could not answer and the user must fill |
| **Draft** | An answer written by the agent (or the local model) awaiting review |
| **Learned answer** | An answer the user typed once, reused for the same question later |
| **Recurring answers** | Standard logistics answers set in the Profile (work authorization, sponsorship, etc.) |
| **Needs you** | The agent is paused waiting on the user |
| **Pending Review** | The form is filled as far as the agent can go; the user checks it and submits |
