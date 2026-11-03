score = int(input("What is our minimum match score? "))
role = input("What is our desired role? ")

job1 = {
    "title": "Senior Product Designer",
    "company": "Microsoft",
    "location": "Canada",
    "remote": True,
    "match_score": 92
}

job2 = {
    "title": "UX Designer",
    "company": "Google",
    "location": "Germany",
    "remote": True,
    "match_score": 88
}

job3 = {
    "title": "Product Designer",
    "company": "Spotify",
    "location": "Sweden",
    "remote": False,
    "match_score": 76
}

jobs = [job1, job2, job3]


def matches_job(job, score, role):
    normalized_role = role.lower().strip()
    return(
        job["match_score"] >= score
        and (job["remote"] or job["location"] == "Canada")
        and normalized_role in job["title"].lower()
    )

for job in jobs:
    if matches_job(job, score, role):
        print(f"\n{job['company']} - {job['title']}")
        print(f"location: {job['location']}")
        print(f"remote: {job['remote']}")
        print(f"match_score: {job['match_score']}%")
