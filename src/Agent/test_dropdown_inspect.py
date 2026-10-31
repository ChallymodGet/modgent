from playwright.sync_api import sync_playwright

APPLICATION_URL = "https://job-boards.greenhouse.io/remotecom/jobs/7762220003"

fields_to_check = [
    "How did you hear about Remote",
    "Are you legally eligible to work",
    "Do you have a non-compete",
]

with sync_playwright() as p:
    browser = p.chromium.launch(headless=False, channel="msedge")
    page = browser.new_page()
    page.goto(APPLICATION_URL)

    page.wait_for_timeout(3000)

    apply_button = page.get_by_text("Apply Now", exact=False)
    apply_button.first.click()
    page.wait_for_timeout(2000)

    for field_name in fields_to_check:
        print(f"\n=== {field_name} ===")
        try:
            combobox = page.get_by_role("combobox", name=field_name)
            combobox.click()
            page.wait_for_timeout(700)

            options = page.locator("[class*='select__option']")
            for i in range(options.count()):
                print(f"  '{options.nth(i).inner_text().strip()}'")

            page.keyboard.press("Escape")
            page.wait_for_timeout(300)
        except Exception as e:
            print(f"  Error: {e}")

    input("\nDone inspecting. Press Enter to close...")
    browser.close()