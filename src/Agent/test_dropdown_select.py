from playwright.sync_api import sync_playwright
from form_filler import select_dropdown_option

APPLICATION_URL = "https://job-boards.greenhouse.io/remotecom/jobs/7762220003"

with sync_playwright() as p:
    browser = p.chromium.launch(headless=False, channel="msedge")
    page = browser.new_page()
    page.goto(APPLICATION_URL)

    page.wait_for_timeout(3000)

    apply_button = page.get_by_text("Apply Now", exact=False)
    apply_button.first.click()
    page.wait_for_timeout(2000)

    sponsorship_input = page.get_by_role("combobox", name="Will you require sponsorship")

    print("Attempting to select 'No' for sponsorship...")
    result = select_dropdown_option(page, sponsorship_input, "Maybe")

    print(f"\nSelection successful: {result}")

    input("\nCheck the dropdown in the browser — does it show 'Maybe' selected? Press Enter to close...")
    browser.close()