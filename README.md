# AI Job Agent - Full Stack Automation System

## Current State: 🚀 API Integration Phase
The project has evolved from a headless automation engine to a professional, full-stack application. We have completed the "Bottom-Up" design process, ensuring the visual system is locked-in and the backend engine is robust before the final wiring.

### 1. Design System & UI (Complete)
We implemented a strict "Engineering-led Monochrome" aesthetic (inspired by Linear and Vercel) to ensure professional consistency:
- **Tokens**: Source of truth for colors (Deep Indigo accents, neutral surfaces), typography (Geist/Inter & JetBrains Mono), and a strict 8px spacing base unit.
- **Component Library**: A tiered React library:
    - **Atoms**: `Button`, `StatusBadge`, `Input`, `ConfidenceIndicator`.
    - **Molecules**: `JobCard` (high-density summaries), `AgentLogEntry` (machine-thought feed).
    - **Organisms**: `ApplicationStepper` (process tracking) and `DiffReviewModal` (AI-human approval interface).
- **Architecture**: SPA with a job-centric information architecture:
    - **Command Center**: Priority-focused dashboard for immediate actions.
    - **The Hunt**: Master job board with advanced filtering.
    - **The Lab**: Candidate intelligence and profile management.
    - **The Ledger**: Transparent audit trail of agent activities.

### 2. Backend Automation Engine (Complete)
A robust data pipeline that automates the job discovery and application process:
- **Profiling**: PDF CV parsing and skill ranking.
- **Discovery**: Async Playwright scraping of multiple job boards.
- **Intelligence**: Semantic match scoring and LLM-powered application tailoring (Llama 3.2).
- **Persistence**: Durable tracking via SQLModel and SQLite.

### 3. Technical Stack
- **Frontend**: React + Tailwind CSS + Lucide React + Vite.
- **Backend**: FastAPI + SQLModel + Async Playwright.
- **Database**: SQLite.

## Roadmap Status
- [x] **Backend: API & Automation Engine**
- [x] **Frontend: Design System & Tokens**
- [x] **Frontend: Atomic Component Library**
- [x] **Frontend: Page Layouts & IA**
- [ ] **Frontend: API Integration (Connecting UI to Backend)**
- [ ] **Final E2E Testing & Polishing**

## Next Step: API Integration
The final phase is replacing mock data with real-time data from the FastAPI server, enabling the user to trigger actual job searches and manage applications directly through the UI.
