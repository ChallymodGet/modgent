# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Common Commands

### Development
- **Run Main Pipeline**: `python src/Agent/main.py`
- **Run Tests**: `pytest`
- **Run Single Test**: `pytest tests/test_<file_name>.py`

## Architecture & Structure

### High-Level Flow
The AI Job Agent is designed as a data pipeline that automates the job discovery and application process. The primary flow is implemented in `src/Agent/main.py`:
1. **Candidate Profiling**: Extracts text from a PDF CV (`parse_cv.py`), builds a profile, and ranks core skills.
2. **Job Discovery**: Scrapes multiple job boards for roles matching specified keywords (`scraper.py`).
3. **Normalization**: Groups duplicate postings cross-listed on different boards (`pipeline.py`).
4. **Scoring**: Evaluates the match between the candidate's skills/roles and the job description (`job_scorer.py`).
5. **Filtering**: Keeps only jobs that meet a minimum match score threshold.
6. **Persistence**: Saves qualifying jobs into a SQLite database (`database.py`) for tracking.

### Project Structure
- `src/Agent/`: Core logic of the job agent.
    - `main.py`: Orchestrates the end-to-end pipeline.
    - `scraper.py`: Handles web scraping of job boards.
    - `job_scorer.py`: Logic for calculating match percentages.
    - `database.py`: SQLite interface for storing and updating job statuses.
    - `form_filler.py`: Logic for automating job application forms.
    - `parse_cv.py` / `read_cv.py`: CV parsing and profile extraction.
- `src/Lesson/`: Contains educational scripts and experiments.
- `tests/`: Pytest suite for verifying pipeline components and database operations.
- `jobs.db`: SQLite database storing discovered jobs and their application status.
- `browser_profile/`: Stores session data to maintain authentication for scraped sites.
