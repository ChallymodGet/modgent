score = int(input("What is our minimum match score? "))

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

for job in jobs:
    print(f"\n{job['company']} - {job['title']}")
    print(f"match_score: {job['match_score']}%")

    if job['match_score'] >= score:
        print("Great match! Consider applying.")

    else:
        print("Skip this job.")