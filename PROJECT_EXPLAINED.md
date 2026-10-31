# Project Explanation: AI Job Agent (Professional Overview)

## The Big Picture
The AI Job Agent is a high-performance automation system designed to replace the manual drudgery of job hunting. It converts the job search process into a structured data pipeline: discovering roles, scoring them against a candidate's actual skills, and automating the application flow.

## How it Works

### 1. The Intelligence Layer (AI & Logic)
The agent operates with a "match-first" philosophy:
- **Deep Profiling**: It parses PDF resumes to extract a structured professional identity and rank core competencies.
- **Strategic Hunting**: Using headless browser automation, it sweeps job boards for roles that fit the candidate's trajectory.
- **Algorithmic Scoring**: It doesn't just keyword match; it evaluates the semantic fit between a job description and the candidate's profile, producing a confidence percentage.
- **AI-Powered Tailoring**: It utilizes LLMs (like Llama 3.2) to generate bespoke application answers based on real evidence from the candidate's history.

### 2. The Automation Engine (Async Playwright)
The system uses **Playwright** to control a real browser instance (Microsoft Edge):
- **Asynchronous Execution**: The engine handles high-volume scraping and form-filling in the background, ensuring the user interface remains responsive.
- **Human-Mimicry**: By using "Persistent Browser Profiles," the agent maintains active sessions and cookies, bypassing bot detection and avoiding repetitive login prompts.

### 3. The Data Core (SQLite)
Every discovery and action is logged in a durable SQLite database:
- **Job Tracking**: Stores title, company, URL, and match score.
- **State Management**: Tracks automation tasks as "Pending," "Running," or "Completed."
- **Intelligence Ledger**: Stores AI-generated drafts for human review and approval.

### 4. The Interface (React + FastAPI)
The system is bridged by a **FastAPI** backend and a professional-grade **React** frontend:
- **Engineering-Led Design**: A high-density, monochrome UI (inspired by Linear/Vercel) provides a "Command Center" experience.
- **Atomic Architecture**: Built from a strict design system of tokens and reusable components (Atoms $\rightarrow$ Molecules $\rightarrow$ Organisms).

## Current Status: Full-Stack Foundation Complete
The project has successfully moved past the "headless" phase. Both the backend automation engine and the high-end frontend UI are fully implemented.

**The Current Focus: API Integration**
We are now in the final integration phase: replacing mock data in the UI with real-time streams from the FastAPI server. This enables the transition from a visual prototype to a live operational tool where users can trigger searches and manage applications in real-time.
