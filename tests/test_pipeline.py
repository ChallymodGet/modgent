from src.Agent.pipeline import filter_jobs_by_score, group_by_posting


def _job(company="Acme", title="Designer", description="Design things", location="Remote"):
    return {"company": company, "title": title, "description": description, "location": location}


def test_group_by_posting_merges_cross_listed_jobs():
    jobs = [_job(location="Remote"), _job(location="London"), _job(title="Engineer")]

    groups = group_by_posting(jobs)

    assert len(groups) == 2
    assert len(groups[("Acme", "Designer", "Design things")]) == 2


def test_group_by_posting_empty():
    assert group_by_posting([]) == {}


def test_filter_jobs_by_score_keeps_jobs_at_or_above_minimum():
    jobs = [{"score": 39}, {"score": 40}, {"score": 90}]

    assert filter_jobs_by_score(jobs, 40) == [{"score": 40}, {"score": 90}]
