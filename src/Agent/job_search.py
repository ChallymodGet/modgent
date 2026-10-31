from playwright.sync_api import sync_playwright

role = input("What job role should we search for? ")

search_url = (
    "https://www.linkedin.com/jobs/search/"
    f"?keywords={role.replace(' ', '%20')}"
)

with sync_playwright() as p:
    browser = p.chromium.launch(headless=False)

    page = browser.new_page()

    print("Opening LinkedIn job search...")

    page.goto(search_url, wait_until="domcontentloaded")

    print(f"Searching for: {role}")
    print(f"Page title: {page.title()}")

    input("\nPress Enter to close the browser...")

    browser.close()