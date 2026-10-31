score = int(input("What is our minimum match score? "))



def get_job_sites():
    return [
        "LinkedIn",
        "Indeed",
        "Wellfound",
        "Glassdoor",
        "Google Jobs"
    ]

def get_job():
    return {
        "title": "Senior Product Designer",
        "company": "Microsoft",
        "location": "Canada",
        "remote": True,
        "match_score": 92
    }



job_sites = get_job_sites()

for site in job_sites:
    print(site)

job = get_job()
print(f"Job Title: {job['title']}")
print(f"Company: {job['company']}")
print(f"match_score: {job['match_score']}")

if job['match_score'] >= score:
    print("Great match! Consider applying.")
else:
    print("Skip this job.")
