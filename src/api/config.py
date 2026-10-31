from pathlib import Path
from typing import Dict

from pydantic_settings import BaseSettings, SettingsConfigDict

# Project root, computed relative to this file so the app is portable across
# machines/users instead of relying on a hardcoded absolute path.
BASE_DIR = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    """
    Infrastructure defaults only. Personal/candidate information (name,
    contact details, recurring answers, CV, target roles, etc.) is NOT
    hardcoded here anymore — it lives in the `Profile` database row and is
    editable from the frontend (Settings/Lab page). These fields are used
    only to seed that row the very first time the app starts.
    """

    # Seed values for the first-run Profile row. Safe, generic defaults —
    # update them from the UI after first launch.
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

    recurring_answers: Dict[str, str] = {
        "work_authorization": "Yes",
        "sponsorship_required": "No",
        "how_heard": "LinkedIn job posting",
        "non_compete": "No",
        "willing_to_relocate": "Open to remote and relocation",
        "years_experience": "",
        "salary_expectation": "",
    }

    # Storage locations — all relative to the project root so the app works
    # the same regardless of which machine/user account runs it.
    db_path: str = str(BASE_DIR / "jobs.db")
    uploads_dir: str = str(BASE_DIR / "data" / "cv")
    browser_profile_path: str = str(BASE_DIR / "browser_profile" / "app_session")
    # Separate from the logged-in apply profile. LinkedIn challenges that
    # saved login, and a signed-out profile can still read public listings.
    browser_search_profile_path: str = str(BASE_DIR / "browser_profile" / "search_session")
    browser_channel: str = "msedge"

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")


settings = Settings()
