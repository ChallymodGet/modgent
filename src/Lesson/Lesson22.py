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
        "status": "Not Applied"
        },

        {
        "title": "UX Designer",
        "company": "Google",
        "location": "Germany",
        "remote": True,
        "match_score": 88,
        "status": "Not Applied"
        },

        {
        "title": "Product Designer",
        "company": "Spotify",
        "location": "Sweden",
        "remote": False,
        "match_score": 76,
        "status": "Not Applied"
        }
    ]

    return jobs

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



for job in jobs:
    if matches_job(job, score, roles, location):
        print(f"\n{job['company']} - {job['title']}")
        print(f"location: {job['location']}")
        print(f"remote: {job['remote']}")
        print(f"match_score: {job['match_score']}%")
        print(f"status: {job['status']}")
