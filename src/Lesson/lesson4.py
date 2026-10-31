site_search = int(input("How many job sites would you like to search? "))




job_sites = [
    "LinkedIn",
    "Indeed",
    "Wellfound",
    "Glassdoor",
    "Google Jobs"
]

companies = [
    "Google",
    "Microsoft",
    "Meta",
    "Spotify",
    "Netflix"
]

if site_search <= 0:
    print("Please enter a number greater than zero.")

elif site_search < 3:
    print("You should search at least 3 job sites for better results.")

if site_search > len(job_sites):
    print("Only 5 job sites are available.")
    print("Searching all available job sites...\n")
    site_search = len(job_sites)

print("\nSearching job sites...\n")
for i in range(site_search):
    print(f"Searching {job_sites[i]}...")