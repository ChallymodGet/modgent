def greet_user(name):
    print(f"\nWelcome, {name}!")


def search_jobs(role, country):
    print(f"Searching for {role} jobs in {country}...\n")

companies = [
        "Google",
        "Microsoft",
        "Meta",
        "Spotify",
        "Netflix"
    ]

def display_companies(companies):

    print("Top companies hiring:")
    for company in companies:
        print(f"- {company}")

def goodbye():
    print("\nThank you for using the AI Job Agent. Good luck with your job search!")

name = input("Name: ")
role = input("Role: ")
country = input("Country: ")

greet_user(name)
search_jobs(role, country)
display_companies(companies)
goodbye()