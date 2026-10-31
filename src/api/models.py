import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional

from pydantic import BaseModel
from sqlmodel import Field, Session, SQLModel, create_engine, select

from src.api.config import settings

# Database Configuration — path is derived from Settings (project-relative,
# overridable via AI_JOB_AGENT env vars / .env), not a hardcoded machine path.
Path(settings.db_path).parent.mkdir(parents=True, exist_ok=True)
DB_PATH = f"sqlite:///{settings.db_path}"
engine = create_engine(DB_PATH, echo=False)

# --- Models ---


class Job(SQLModel, table=True):
    __tablename__ = "jobs"

    job_id: str = Field(primary_key=True)
    title: str
    company: str
    location: str
    url: str
    description: str
    match_score: int
    source: str
    status: str = Field(default="Not Reviewed")
    date_added: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class Task(SQLModel, table=True):
    __tablename__ = "tasks"

    task_id: str = Field(primary_key=True)
    task_type: str  # 'discovery' or 'apply'
    status: str  # 'pending', 'running', 'completed', 'failed'
    job_id: Optional[str] = Field(default=None, foreign_key="jobs.job_id")
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    result: Optional[str] = None
    progress: Optional[str] = None


class ApplicationAnswer(SQLModel, table=True):
    __tablename__ = "answers"

    answer_id: Optional[int] = Field(default=None, primary_key=True)
    job_id: str = Field(foreign_key="jobs.job_id")
    question: str
    draft_answer: str
    final_answer: Optional[str] = None
    # Newline-separated options when the question is a choice (Yes/No, a dropdown).
    choices: Optional[str] = None
    # text, select, radio, or checkbox. Checkbox answers can contain more than one choice.
    kind: Optional[str] = None
    is_reviewed: bool = Field(default=False)


class LearnedAnswer(SQLModel, table=True):
    """
    An answer the user typed because the agent had no match for that
    question. The next application that asks the same thing is filled
    from this row instead of being left blank.
    """

    __tablename__ = "learned_answers"

    id: Optional[int] = Field(default=None, primary_key=True)
    question_key: str = Field(unique=True, index=True)
    question: str
    answer: str
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class Profile(SQLModel, table=True):
    """
    Single-row table holding the candidate's personal details, target-role
    preferences, recurring application answers, and CV location. Replaces
    the hardcoded values that used to live in config.py / contact_info.py /
    application_preferences.py — all of it is now editable from the UI.
    """

    __tablename__ = "profile"

    id: int = Field(default=1, primary_key=True)
    name: str = ""
    email: str = ""
    phone: str = ""
    linkedin_url: str = ""
    portfolio_url: str = ""
    location: str = ""
    country: str = ""
    job_search_location: str = "United States"
    target_roles: str = "Product Designer"
    min_match_score: int = 40
    recurring_answers_json: str = "{}"
    cv_path: str = ""
    cv_filename: str = ""
    cv_uploaded_at: Optional[datetime] = None

    def recurring_answers(self) -> Dict[str, str]:
        try:
            return json.loads(self.recurring_answers_json) or {}
        except (TypeError, ValueError):
            return {}

    def set_recurring_answers(self, answers: Dict[str, str]) -> None:
        self.recurring_answers_json = json.dumps(answers or {})

    def has_cv(self) -> bool:
        return bool(self.cv_path) and Path(self.cv_path).is_file()


# --- API-facing schemas (not DB tables) ---


class RecurringAnswers(BaseModel):
    work_authorization: str = "Yes"
    sponsorship_required: str = "No"
    how_heard: str = "LinkedIn job posting"
    non_compete: str = "No"
    willing_to_relocate: str = "Open to remote and relocation"
    years_experience: str = ""
    salary_expectation: str = ""


class ProfileUpdate(BaseModel):
    name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    linkedin_url: Optional[str] = None
    portfolio_url: Optional[str] = None
    location: Optional[str] = None
    country: Optional[str] = None
    job_search_location: Optional[str] = None
    target_roles: Optional[str] = None
    min_match_score: Optional[int] = None
    recurring_answers: Optional[Dict[str, str]] = None


class ProfileOut(BaseModel):
    name: str
    email: str
    phone: str
    linkedin_url: str
    portfolio_url: str
    location: str
    country: str
    job_search_location: str
    target_roles: str
    min_match_score: int
    recurring_answers: Dict[str, str]
    cv_filename: str
    cv_uploaded_at: Optional[datetime]
    has_cv: bool


class AnswerUpdate(BaseModel):
    answer_id: int
    final_answer: str


def profile_to_out(profile: Profile) -> ProfileOut:
    return ProfileOut(
        name=profile.name,
        email=profile.email,
        phone=profile.phone,
        linkedin_url=profile.linkedin_url,
        portfolio_url=profile.portfolio_url,
        location=profile.location,
        country=profile.country,
        job_search_location=profile.job_search_location,
        target_roles=profile.target_roles,
        min_match_score=profile.min_match_score,
        recurring_answers=profile.recurring_answers(),
        cv_filename=profile.cv_filename,
        cv_uploaded_at=profile.cv_uploaded_at,
        has_cv=profile.has_cv(),
    )


# --- Database Operations ---


def init_db():
    SQLModel.metadata.create_all(engine)
    _migrate_add_missing_columns()


def _migrate_add_missing_columns():
    """
    SQLModel's create_all() only creates tables that don't exist yet — it
    never alters existing ones. Since `tasks.job_id` was added after this
    project's jobs.db was first created, add it here if it's missing so
    existing databases don't break instead of requiring a full migration
    tool for one column.
    """
    import sqlalchemy as sa

    inspector = sa.inspect(engine)
    statements = []
    tables = set(inspector.get_table_names())

    if "tasks" in tables:
        existing_columns = {col["name"] for col in inspector.get_columns("tasks")}
        if "job_id" not in existing_columns:
            statements.append("ALTER TABLE tasks ADD COLUMN job_id VARCHAR")
        if "progress" not in existing_columns:
            statements.append("ALTER TABLE tasks ADD COLUMN progress VARCHAR")

    if "answers" in tables:
        answer_columns = {col["name"] for col in inspector.get_columns("answers")}
        if "choices" not in answer_columns:
            statements.append("ALTER TABLE answers ADD COLUMN choices VARCHAR")
        if "kind" not in answer_columns:
            statements.append("ALTER TABLE answers ADD COLUMN kind VARCHAR")

    if statements:
        with engine.begin() as conn:
            for statement in statements:
                conn.execute(sa.text(statement))


def get_session():
    with Session(engine) as session:
        yield session


def get_or_create_profile(session: Session) -> Profile:
    """
    Returns the single Profile row, creating it from the Settings() seed
    values the first time the app runs.
    """
    profile = session.get(Profile, 1)
    if profile:
        return profile

    profile = Profile(
        id=1,
        name=settings.name,
        email=settings.email,
        phone=settings.phone,
        linkedin_url=settings.linkedin_url,
        portfolio_url=settings.portfolio_url,
        location=settings.location,
        country=settings.country,
        job_search_location=settings.job_search_location,
        target_roles=settings.target_roles,
        min_match_score=settings.min_match_score,
    )
    profile.set_recurring_answers(settings.recurring_answers)
    session.add(profile)
    session.commit()
    session.refresh(profile)
    return profile


# Utility functions to maintain some compatibility with old database.py logic
def save_job(job_data: dict, score: int):
    with Session(engine) as session:
        # Check if exists
        statement = select(Job).where(Job.job_id == job_data["job_id"])
        existing = session.exec(statement).first()
        if not existing:
            job = Job(
                job_id=job_data["job_id"],
                title=job_data["title"],
                company=job_data["company"],
                location=job_data["location"],
                url=job_data["url"],
                description=job_data["description"],
                match_score=score,
                source=job_data.get("source", "Unknown"),
            )
            session.add(job)
            session.commit()
            session.refresh(job)
            return job
    return None


def update_job_status(job_id: str, status: str):
    with Session(engine) as session:
        job = session.get(Job, job_id)
        if job:
            job.status = status
            session.add(job)
            session.commit()
            session.refresh(job)
            return job
    return None


def get_all_jobs() -> List[Job]:
    with Session(engine) as session:
        return session.exec(select(Job).order_by(Job.match_score.desc())).all()


def get_jobs_by_status(status: str) -> List[Job]:
    with Session(engine) as session:
        return session.exec(
            select(Job).where(Job.status == status).order_by(Job.match_score.desc())
        ).all()
