score = int(input("What is our minimum match score? "))
location = input("What is our desired location? ")

roles = [
    input("What is our desired role? "),
    input("What is another acceptable role? "),
    input("What is a third acceptable role? ")
]

def create_jobs():
    jobs = [
        {
        "title": "Senior Product Designer",
        "company": "Microsoft",
        "location": "Canada",
        "remote": True,
        "match_score": 92,
        "status": "Not Reviewed"
        },

        {
        "title": "UX Designer",
        "company": "Google",
        "location": "Germany",
        "remote": True,
        "match_score": 88,
        "status": "Not Reviewed"
        },

        {
        "title": "Product Designer",
        "company": "Spotify",
        "location": "Sweden",
        "remote": False,
        "match_score": 76,
        "status": "Not Reviewed"
        }
    ]

    return jobs

def apply_to_job(job):
    job["status"] = "Applied"
    print(f"Applied to {job['company']} - {job['title']}")

jobs = create_jobs()

def matches_job(job, score, roles, location):
    normalized_roles = []

    for role in roles:
        normalized_roles.append(role.lower().strip())

    job_title = job["title"].lower()
    job_location = job["location"].lower()
    normalized_location = location.lower().strip()


    return(
        job["match_score"] >= score
        and (job["remote"] or job_location == normalized_location)
        and any(role in job_title for role in normalized_roles)
    )

def process_job(job, score, roles, location):
    if matches_job(job, score, roles, location) and job["status"] == "Not Reviewed":
        print(f"\n{job['company']} - {job['title']}")
        print(f"location: {job['location']}")
        print(f"remote: {job['remote']}")
        print(f"match_score: {job['match_score']}%")
        print(f"status: Matched")

        apply_to_job(job)

for job in jobs:
    process_job(job, score, roles, location)
