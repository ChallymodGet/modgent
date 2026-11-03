score = int(input("What is our minimum match score? "))
role = input("What is our desired role? ")
second_role = input("What is another acceptable role? ")


def get_jobs():
    jobs = [
        {
        "title": "Senior Product Designer",
        "company": "Microsoft",
        "location": "Canada",
        "remote": True,
        "match_score": 92
        },

        {
        "title": "UX Designer",
        "company": "Google",
        "location": "Germany",
        "remote": True,
        "match_score": 88
        },

        {
        "title": "Product Designer",
        "company": "Spotify",
        "location": "Sweden",
        "remote": False,
        "match_score": 76
        }
    ]

    return jobs

jobs = get_jobs()

def matches_job(job, score, role, second_role):
    normalized_role = role.lower().strip()
    normalized_second_role = second_role.lower().strip()
    job_title = job["title"].lower()


    return(
        job["match_score"] >= score
        and (job["remote"] or job["location"] == "Canada")
        and (normalized_role in job_title
             or normalized_second_role in job_title)
    )


for job in jobs:
    if matches_job(job, score, role, second_role):
        print(f"\n{job['company']} - {job['title']}")
        print(f"location: {job['location']}")
        print(f"remote: {job['remote']}")
        print(f"match_score: {job['match_score']}%")
