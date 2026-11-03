print("=== AI Job Agent ===")

name = input("What is your name? ")
experience = int(input("How many years of experience do you have? "))
job_type = input("Are you looking for Remote, Hybrid or On-site jobs? ")

print(f"\nWelcome, {name}!")

if experience >= 5:
    print("You qualify for Senior Product Designer roles.")
else:
    print("You should focus on Mid-Level or Junior Product Designer roles.")

if job_type == "Remote":
    print("Great choice! We'll prioritize remote jobs.")
else:
    print("We'll include all matching opportunities.")    