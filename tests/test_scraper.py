import asyncio

from src.Agent import scraper
from src.Agent.scraper import search_all_boards, wellfound_role_slugs


def test_wellfound_role_slugs_follow_target_roles():
    assert wellfound_role_slugs("Product Designer, UX/UI Designer , product designer") == [
        "product-designer",
        "ux-ui-designer",
    ]
    assert wellfound_role_slugs(" , ") == []


def _fake_board(name, delay, fail=False):
    async def search(keywords, location, max_jobs, on_progress=None):
        await asyncio.sleep(delay)
        if fail:
            raise RuntimeError("blocked")
        return [{"job_id": f"{name}-1", "source": name}]
    return search


def test_boards_run_at_once_and_one_failure_keeps_the_rest(monkeypatch):
    monkeypatch.setattr(scraper, "search_linkedin", _fake_board("LinkedIn", 0.3))
    monkeypatch.setattr(scraper, "search_indeed", _fake_board("Indeed", 0.3, fail=True))
    monkeypatch.setattr(scraper, "search_wellfound", _fake_board("Wellfound", 0.3))
    events = []

    async def on_progress(event):
        events.append(event)

    async def run():
        loop = asyncio.get_running_loop()
        start = loop.time()
        jobs = await search_all_boards("Designer", "Remote", on_progress=on_progress)
        return jobs, loop.time() - start

    jobs, elapsed = asyncio.run(run())

    assert [job["source"] for job in jobs] == ["LinkedIn", "Wellfound"]
    assert elapsed < 0.8  # three 0.3 s searches in sequence would take 0.9 s
    assert events[-1]["boards"] == {"LinkedIn": "done", "Indeed": "failed", "Wellfound": "done"}
