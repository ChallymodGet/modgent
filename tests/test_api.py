import asyncio
from datetime import datetime, timedelta, timezone

import pytest
from fastapi import HTTPException

from src.api.config import settings
from src.api.main import list_tasks, update_job_status_api
from src.api.models import Job, Task, mark_interrupted_tasks


def test_tests_use_a_throwaway_database():
    assert "modgent-tests-" in settings.db_path


def _job(session, status="Applied"):
    job = Job(job_id="1", title="Designer", company="Acme", location="Remote",
              url="https://example.com", description="", match_score=80, source="LinkedIn", status=status)
    session.add(job)
    session.commit()
    return job


@pytest.mark.parametrize("status", ["Interviewing", "Offer", "Ghosted", "Applied"])
def test_user_can_set_post_application_statuses(session, status):
    _job(session)

    job = asyncio.run(update_job_status_api("1", status, session))

    assert job.status == status


def test_unknown_status_is_rejected(session):
    _job(session)

    with pytest.raises(HTTPException) as error:
        asyncio.run(update_job_status_api("1", "Interviewed", session))

    assert error.value.status_code == 400


def test_list_tasks_returns_newest_first(session):
    now = datetime.now(timezone.utc)
    for i in range(3):
        session.add(Task(task_id=f"t{i}", task_type="discovery", status="completed",
                         created_at=now + timedelta(minutes=i)))
    session.commit()

    tasks = asyncio.run(list_tasks(limit=2, session=session))

    assert [task.task_id for task in tasks] == ["t2", "t1"]


def test_tasks_left_running_by_a_stopped_server_are_failed(session):
    session.add(Task(task_id="running", task_type="apply", status="running"))
    session.add(Task(task_id="done", task_type="apply", status="completed"))
    session.commit()

    assert mark_interrupted_tasks() == 1

    session.expire_all()
    assert session.get(Task, "running").status == "failed"
    assert session.get(Task, "done").status == "completed"
