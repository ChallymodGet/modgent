import os
import sys

# Add the project root to the Python path to support package imports
project_root = os.path.dirname(os.path.abspath(__file__))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from sqlmodel import Session

from src.Agent.parse_cv import build_candidate_summary
from src.Agent.read_cv import extract_cv_text
from src.api.models import engine, get_or_create_profile, get_all_jobs


def test_application():
    print("--- AI Job Agent: Form-Filler Test Run ---")

    # 1. Get the highest scoring job from the database
    jobs = get_all_jobs()
    if not jobs:
        print("No jobs found in database. Please run discovery first.")
        return

    top_job = jobs[0]
    job_dict = {
        "job_id": top_job.job_id,
        "title": top_job.title,
        "company": top_job.company,
        "location": top_job.location,
        "url": top_job.url,
        "description": top_job.description,
        "score": top_job.match_score,
        "source": top_job.source,
    }

    print(f"Testing application for: {job_dict['company']} - {job_dict['title']} (Score: {job_dict['score']}%)")
    print(f"URL: {job_dict['url']}")

    # 2. Generate the candidate summary from the CV on file in the Profile
    print("\nGenerating candidate summary from CV...")
    try:
        with Session(engine) as session:
            profile = get_or_create_profile(session)
            if not profile.has_cv():
                raise RuntimeError("No CV uploaded. Upload one via the Profile tab/API first.")
            cv_text = extract_cv_text(profile.cv_path)
        candidate_summary = build_candidate_summary(cv_text)
    except Exception as e:
        print(f"Could not parse CV for summary: {e}")
        candidate_summary = "Experienced Senior Product Designer with expertise in UI/UX, AI tools, and Product Strategy."

    # 3. Run the application process
    # Note: apply_to_job is async and requires a session + profile data.
    # Since this is a simple test script, we just confirm readiness here —
    # use the FastAPI endpoints (POST /automation/apply/{job_id}) or the
    # frontend UI to actually run the automation.
    print("\n[NOTICE] The application runner is Asynchronous and profile-driven.")
    print("To test the automation, please use the new Frontend UI or the FastAPI endpoints.")
    print("\nSample data extracted for test:")
    print(f"Target Job: {job_dict['title']}")
    print(f"Candidate Summary: {candidate_summary[:100]}...")


if __name__ == "__main__":
    test_application()
