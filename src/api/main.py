import asyncio
import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional

from fastapi import BackgroundTasks, Depends, FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from sqlmodel import Session, select

from src.Agent import session_registry
from src.Agent.application_runner import advance_application, apply_to_job
from src.Agent.form_filler import (
    apply_final_answers_to_page,
    find_learned_answer,
    harvest_user_filled_fields,
    load_learned_map,
    remember_answer,
)
from src.Agent.job_scorer import score_job
from src.Agent.parse_cv import build_candidate_summary, build_skills_from_cv
from src.Agent.pipeline import filter_jobs_by_score, group_by_posting
from src.Agent.read_cv import extract_cv_text
from src.Agent.scraper import search_all_boards
from src.api.config import settings
from src.api.models import (
    JOB_STATUSES,
    AnswerUpdate,
    ApplicationAnswer,
    Job,
    LearnedAnswer,
    ProfileOut,
    ProfileUpdate,
    Task,
    engine,
    get_or_create_profile,
    get_session,
    profile_to_out,
    save_job,
    update_job_status,
)

app = FastAPI(
    title="AI Job Agent API",
    description="Backend API for discovering and applying to jobs using AI automation",
    version="1.0.0",
)

# Enable CORS for frontend integration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
async def on_startup():
    from src.api.models import init_db, mark_interrupted_tasks

    init_db()
    # Background tasks die with the server. Without this, a run that was in
    # progress at shutdown would show as running in the Ledger forever.
    mark_interrupted_tasks()


# --- Utility Background Tasks ---


async def run_discovery_task(task_id: str):
    """
    Background task that runs the full job discovery pipeline: scrape ->
    dedupe cross-listed postings -> score against the candidate's ACTUAL
    CV (skills) and target roles -> keep only jobs that meet the profile's
    minimum match score -> save.
    """
    with Session(engine) as session:
        task = session.get(Task, task_id)
        if task:
            task.status = "running"
            session.add(task)
            session.commit()

        try:
            latest: dict = {}

            async def publish(event: dict):
                latest.update(event)
                if not task:
                    return
                task.progress = json.dumps(event)
                task.result = event.get("message")
                task.updated_at = datetime.now(timezone.utc)
                session.add(task)
                session.commit()

            profile = get_or_create_profile(session)
            if not profile.has_cv():
                raise RuntimeError(
                    "No CV uploaded. Upload a CV in the Profile tab before running discovery."
                )
            if not profile.target_roles.strip():
                raise RuntimeError(
                    "No target roles set. Add at least one target role in the Profile tab."
                )

            roles = [r.strip() for r in profile.target_roles.split(",") if r.strip()]

            # CV parsing/scoring is CPU-bound and uses blocking I/O (pdfplumber),
            # so it's offloaded to a worker thread instead of blocking the
            # event loop that the scraper and the rest of the API share.
            await publish({
                "phase": "preparing",
                "found": 0,
                "message": "Reading your CV",
                "boards": {"LinkedIn": "waiting", "Indeed": "waiting", "Wellfound": "waiting"},
                "counts": {},
            })
            core_skills = await asyncio.to_thread(build_skills_from_cv, profile.cv_path)

            print(f"Starting discovery run for: {profile.target_roles}")
            jobs = await search_all_boards(
                keywords=profile.target_roles,
                location=profile.job_search_location,
                on_progress=publish,
            )

            await publish({
                "phase": "scoring",
                "found": len(jobs),
                "message": f"Scoring {len(jobs)} listings against your CV",
                "boards": latest.get("boards", {}),
                "counts": latest.get("counts", {}),
            })

            # Dedupe postings cross-listed under identical company/title/description
            # (this grouping used to be computed and then silently thrown away).
            grouped = group_by_posting(jobs)
            deduped_jobs = [postings[0] for postings in grouped.values()]

            scored_jobs = [
                {**job_data, "score": score_job(job_data, roles, core_skills)}
                for job_data in deduped_jobs
            ]

            qualifying_jobs = filter_jobs_by_score(scored_jobs, profile.min_match_score)

            count = 0
            for job_data in qualifying_jobs:
                if save_job(job_data, job_data["score"]):
                    count += 1

            if task:
                task.status = "completed"
                task.result = (
                    f"Scraped {len(jobs)} postings, {len(deduped_jobs)} unique after dedup, "
                    f"{len(qualifying_jobs)} met the {profile.min_match_score}% match threshold, "
                    f"saved {count} new job(s)."
                )
                session.add(task)
                session.commit()
        except Exception as e:
            if task:
                task.status = "failed"
                task.result = str(e)
                session.add(task)
                session.commit()


_OUTCOMES = {
    "needs_you": (
        "This page has required fields only you can answer. "
        "Answer them in the review window. They're saved for next time, then the agent continues."
    ),
    "review": "Stopped on Review. Check the form, click Submit yourself, then mark the job Applied.",
    "stopped": "Paused on the open application. Fill anything still blank in the window, then click Continue.",
}

# Said before the outcome when the user had closed the window and the agent
# opened the application again. The outcome itself still decides what the UI
# does next (a reopened form can still need the review window).
_REOPENED_NOTE = "The application window was closed, so it was opened again. "


def _public_error(exc: Exception) -> str:
    text = str(exc)
    lowered = text.lower()
    if "already in use" in lowered or "existing browser session" in lowered:
        return (
            "An application window is already open. Close it, then click Apply again. "
            "If that window is this application, click Continue on the job."
        )
    first = text.strip().splitlines()[0] if text.strip() else "The application could not be opened."
    return first[:300]


def _finish_apply_task(session: Session, task: Optional[Task], outcome: str, reopened: bool = False) -> None:
    if not task:
        return
    task.status = "completed"
    task.progress = json.dumps({"phase": outcome, "reopened": reopened})
    task.result = (_REOPENED_NOTE if reopened else "") + _OUTCOMES.get(outcome, _OUTCOMES["stopped"])
    task.updated_at = datetime.now(timezone.utc)
    session.add(task)
    session.commit()


async def _load_candidate(session: Session):
    profile = get_or_create_profile(session)
    if not profile.has_cv():
        raise RuntimeError("No CV uploaded. Upload a CV in the Profile tab before applying to jobs.")
    cv_text = await asyncio.to_thread(extract_cv_text, profile.cv_path)
    summary = await asyncio.to_thread(build_candidate_summary, cv_text)
    return summary, _contact_from_profile(profile), profile.recurring_answers(), profile.cv_path, profile.cv_filename, cv_text


async def run_application_task(task_id: str, job_id: str):
    """
    Background task that runs the application automation for a specific
    job, using the candidate's real CV summary and Profile details instead
    of a hardcoded placeholder summary.
    """
    with Session(engine) as session:
        task = session.get(Task, task_id)
        if task:
            task.status = "running"
            task.job_id = job_id
            session.add(task)
            session.commit()

        try:
            if task:
                task.result = "Waiting for the application page to finish loading."
                task.progress = json.dumps({"phase": "loading"})
                session.add(task)
                session.commit()
            summary, contact, recurring, cv_path, cv_name, cv_text = await _load_candidate(session)
            job = session.get(Job, job_id)
            if not job:
                raise RuntimeError("Job not found")

            reopened = await session_registry.drop_if_closed(job_id)
            live = await session_registry.get_session(job_id)
            if live is not None:
                outcome = await advance_application(
                    live["page"], job, summary, contact, recurring, cv_path, session,
                    replay=True, cv_name=cv_name, cv_text=cv_text,
                )
            else:
                outcome = await apply_to_job(
                    job_id, summary, contact, recurring, cv_path, session,
                    cv_name=cv_name, cv_text=cv_text,
                )

            _finish_apply_task(session, task, outcome or "stopped", reopened)
        except Exception as e:
            if task:
                task.status = "failed"
                task.result = _public_error(e)
                task.updated_at = datetime.now(timezone.utc)
                session.add(task)
                session.commit()


async def continue_application_task(task_id: str, job_id: str):
    """Keeps filling the application that is already open, after the user answers or moves ahead."""
    with Session(engine) as session:
        task = session.get(Task, task_id)
        if task:
            task.status = "running"
            task.job_id = job_id
            session.add(task)
            session.commit()

        try:
            if task:
                task.result = "Waiting for the application page to finish loading."
                task.progress = json.dumps({"phase": "loading"})
                session.add(task)
                session.commit()
            job = session.get(Job, job_id)
            if not job:
                raise RuntimeError("Job not found")
            reopened = await session_registry.drop_if_closed(job_id)
            live = await session_registry.get_session(job_id)
            summary, contact, recurring, cv_path, cv_name, cv_text = await _load_candidate(session)
            if live is None:
                outcome = await apply_to_job(
                    job_id, summary, contact, recurring, cv_path, session,
                    cv_name=cv_name, cv_text=cv_text,
                )
                _finish_apply_task(session, task, outcome or "stopped", reopened)
                return
            await harvest_user_filled_fields(live["page"], contact, recurring, session)
            outcome = await advance_application(
                live["page"], job, summary, contact, recurring, cv_path, session,
                replay=True, cv_name=cv_name, cv_text=cv_text,
            )
            _finish_apply_task(session, task, outcome or "stopped")
        except Exception as e:
            if task:
                task.status = "failed"
                task.result = _public_error(e)
                task.updated_at = datetime.now(timezone.utc)
                session.add(task)
                session.commit()


# --- Endpoints ---


@app.get("/")
async def root():
    return {"message": "AI Job Agent API is running", "docs": "/docs"}


@app.get("/jobs", response_model=List[Job])
async def list_jobs(status: Optional[str] = None, session: Session = Depends(get_session)):
    if status:
        return session.exec(
            select(Job).where(Job.status == status).order_by(Job.match_score.desc())
        ).all()
    return session.exec(select(Job).order_by(Job.match_score.desc())).all()


@app.get("/jobs/{job_id}", response_model=Job)
async def get_job(job_id: str, session: Session = Depends(get_session)):
    job = session.get(Job, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return job


@app.patch("/jobs/{job_id}")
async def update_job_status_api(job_id: str, status: str, session: Session = Depends(get_session)):
    if status not in JOB_STATUSES:
        raise HTTPException(
            status_code=400,
            detail=f"Unknown status '{status}'. Use one of: {', '.join(JOB_STATUSES)}.",
        )
    job = update_job_status(job_id, status)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    # Once the human has actually applied (or abandoned the job), there's no
    # reason to keep its browser session open any longer.
    if status == "Applied":
        await session_registry.drop_if_closed(job_id)
        live_session = await session_registry.get_session(job_id)
        if live_session is not None:
            profile = get_or_create_profile(session)
            await harvest_user_filled_fields(
                live_session["page"],
                _contact_from_profile(profile),
                profile.recurring_answers(),
                session,
            )

    if status in ("Applied", "Ghosted"):
        await session_registry.close_session(job_id)

    return job


def _learned_note(count: int) -> str:
    if count == 1:
        return " Saved 1 answer for the next time this question appears."
    if count > 1:
        return f" Saved {count} answers for the next time these questions appear."
    return ""


def _contact_from_profile(profile) -> dict:
    return {
        "name": profile.name,
        "email": profile.email,
        "phone": profile.phone,
        "linkedin_url": profile.linkedin_url,
        "portfolio_url": profile.portfolio_url,
        "location": profile.location,
        "country": profile.country,
    }


# --- Profile (personal details, recurring answers, CV) ---


@app.get("/profile", response_model=ProfileOut)
async def get_profile(session: Session = Depends(get_session)):
    profile = get_or_create_profile(session)
    return profile_to_out(profile)


@app.put("/profile", response_model=ProfileOut)
async def update_profile(update: ProfileUpdate, session: Session = Depends(get_session)):
    profile = get_or_create_profile(session)

    data = update.model_dump(exclude_unset=True, exclude={"recurring_answers"})
    for key, value in data.items():
        setattr(profile, key, value)

    if update.recurring_answers is not None:
        profile.set_recurring_answers(update.recurring_answers)

    session.add(profile)
    session.commit()
    session.refresh(profile)
    return profile_to_out(profile)


@app.post("/profile/cv", response_model=ProfileOut)
async def upload_cv(file: UploadFile = File(...), session: Session = Depends(get_session)):
    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are supported for the CV.")

    profile = get_or_create_profile(session)

    uploads_dir = Path(settings.uploads_dir)
    uploads_dir.mkdir(parents=True, exist_ok=True)
    dest_path = uploads_dir / f"cv_{uuid.uuid4().hex}.pdf"

    contents = await file.read()
    dest_path.write_bytes(contents)

    # Clean up the previously uploaded CV file now that it's been replaced.
    previous_path = profile.cv_path
    if previous_path and previous_path != str(dest_path) and Path(previous_path).is_file():
        try:
            Path(previous_path).unlink()
        except OSError:
            pass

    profile.cv_path = str(dest_path)
    profile.cv_filename = file.filename
    profile.cv_uploaded_at = datetime.now(timezone.utc)
    session.add(profile)
    session.commit()
    session.refresh(profile)
    return profile_to_out(profile)


# --- Automation ---


@app.post("/automation/discovery")
async def trigger_discovery(background_tasks: BackgroundTasks):
    task_id = str(uuid.uuid4())
    with Session(engine) as session:
        task = Task(task_id=task_id, task_type="discovery", status="pending")
        session.add(task)
        session.commit()

    background_tasks.add_task(run_discovery_task, task_id)
    return {"task_id": task_id, "status": "started"}


@app.get("/automation/tasks", response_model=List[Task])
async def list_tasks(limit: int = 100, session: Session = Depends(get_session)):
    """Recent discovery and apply runs, newest first, so the Ledger survives a page refresh."""
    limit = max(1, min(limit, 500))
    return session.exec(select(Task).order_by(Task.created_at.desc()).limit(limit)).all()


@app.get("/automation/tasks/{task_id}")
async def get_task_status(task_id: str, session: Session = Depends(get_session)):
    task = session.get(Task, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return task


@app.post("/automation/apply/{job_id}")
async def trigger_apply(job_id: str, background_tasks: BackgroundTasks, session: Session = Depends(get_session)):
    job = session.get(Job, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    profile = get_or_create_profile(session)
    if not profile.has_cv():
        raise HTTPException(
            status_code=400,
            detail="Upload a CV in the Profile tab before applying to jobs.",
        )

    task_id = str(uuid.uuid4())
    task = Task(task_id=task_id, task_type="apply", status="pending", job_id=job_id)
    session.add(task)
    session.commit()

    background_tasks.add_task(run_application_task, task_id, job_id)
    return {"task_id": task_id, "status": "started"}


@app.post("/automation/apply/{job_id}/continue")
async def continue_apply(job_id: str, background_tasks: BackgroundTasks, session: Session = Depends(get_session)):
    """
    Scans the open application again. Use this after answering required
    fields, or after moving to the next page yourself.
    """
    job = session.get(Job, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    task_id = str(uuid.uuid4())
    task = Task(task_id=task_id, task_type="apply", status="pending", job_id=job_id)
    session.add(task)
    session.commit()
    background_tasks.add_task(continue_application_task, task_id, job_id)
    return {"task_id": task_id, "status": "started"}


@app.get("/automation/apply/{job_id}/questions")
async def get_application_questions(job_id: str, session: Session = Depends(get_session)):
    answers = session.exec(select(ApplicationAnswer).where(ApplicationAnswer.job_id == job_id)).all()
    learned = load_learned_map(session)
    payload = []
    for ans in answers:
        data = ans.model_dump()
        saved = find_learned_answer(ans.question, learned)
        data["remembered"] = bool(saved) and saved == ans.draft_answer
        payload.append(data)
    return payload


@app.get("/learned-answers")
async def list_learned_answers(session: Session = Depends(get_session)):
    rows = session.exec(select(LearnedAnswer).order_by(LearnedAnswer.updated_at.desc())).all()
    return rows


@app.delete("/learned-answers/{answer_id}")
async def delete_learned_answer(answer_id: int, session: Session = Depends(get_session)):
    row = session.get(LearnedAnswer, answer_id)
    if not row:
        raise HTTPException(status_code=404, detail="Saved answer not found")
    session.delete(row)
    session.commit()
    return {"status": "deleted"}


@app.post("/automation/apply/{job_id}/answers")
async def submit_answers(job_id: str, answers: List[AnswerUpdate], session: Session = Depends(get_session)):
    """
    Saves the human-reviewed, finalized answers AND, if the job's browser
    session is still open, types them into the live application form.
    This never marks the job "Applied" by itself — the human still has to
    actually look at the form and click Submit, then mark it Applied via
    PATCH /jobs/{job_id}.
    """
    job = session.get(Job, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    finalized: List[tuple] = []
    learned_count = 0
    for item in answers:
        ans = session.get(ApplicationAnswer, item.answer_id)
        if ans and ans.job_id == job_id:
            previous = (ans.draft_answer or "").strip()
            final = (item.final_answer or "").strip()
            ans.final_answer = item.final_answer
            ans.is_reviewed = True
            session.add(ans)
            finalized.append((ans.question, item.final_answer))
            # Only answers the user actually typed or changed are remembered.
            # An untouched AI draft stays a one-off for this job.
            if (
                final
                and final != previous
                and ans.question.strip().lower() != "cover letter"
                and remember_answer(session, ans.question, final)
            ):
                learned_count += 1

    session.commit()

    await session_registry.drop_if_closed(job_id)
    live_session = await session_registry.get_session(job_id)
    if live_session is not None:
        profile = get_or_create_profile(session)
        learned_count += await harvest_user_filled_fields(
            live_session["page"],
            _contact_from_profile(profile),
            profile.recurring_answers(),
            session,
        )

    if live_session is None:
        update_job_status(job_id, "Ready to Submit")
        return {
            "status": (
                "Answers saved, but this job's browser session is no longer open "
                "(e.g. the server restarted). Open the job's application page again "
                "to type these in, then submit manually."
                + _learned_note(learned_count)
            ),
            "typed_into_live_form": False,
            "learned": learned_count,
        }

    result = await apply_final_answers_to_page(live_session["page"], finalized)
    return {
        "status": (
            "Answers saved. The agent is filling the next page."
            + _learned_note(learned_count)
        ),
        "typed_into_live_form": True,
        "learned": learned_count,
        **result,
    }


@app.post("/automation/apply/{job_id}/close")
async def close_apply_session(job_id: str):
    """
    Manually closes a job's lingering browser session (e.g. the user
    abandoned the application without marking it Applied/Ghosted).
    """
    closed = await session_registry.close_session(job_id)
    return {"status": "closed" if closed else "no active session for this job"}
