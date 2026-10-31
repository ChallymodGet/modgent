jobs = [
    {
        "title": "Senior Product Designer",
        "company": "Microsoft",
        "country": "Canada"
    },
    {
        "title": "UX Designer",
        "company": "Google",
        "country": "Germany"
    },
    {
        "title": "Product Designer",
        "company": "Spotify",
        "country": "Sweden"
    }
]

for job in jobs:
    print(f"{job['company']} - {job['title']} ({job['country']})")

user = [
    {
    "name": "Charles Onofuevure",
    "role": "Senior Product Designer",
    "country": "Nigeria",
    "experience": "5 years"
    }
]
for person in user:
    print(person["name"])
    print(person["role"])
    print(person["country"])
    print(person["experience"])
