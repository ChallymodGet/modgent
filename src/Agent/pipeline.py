def group_by_posting(jobs):
    """NORMALIZE/DEDUPLICATE stage — groups jobs that are the same posting
    cross-listed in multiple locations."""
    groups = {}

    for job in jobs:
        key = (job["company"], job["title"], job["description"])

        if key not in groups:
            groups[key] = []

        groups[key].append(job)

    return groups


def filter_jobs_by_score(scored_jobs, minimum_score):
    """FILTER stage — keeps only jobs at or above the minimum score."""
    return [job for job in scored_jobs if job["score"] >= minimum_score]