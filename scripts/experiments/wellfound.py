from playwright.sync_api import sync_playwright

with sync_playwright() as p:

    browser = p.chromium.launch(headless=False)
    page = browser.new_page()

    page.goto(
        "https://wellfound.com/role/product-designer"
    )

    print("Wellfound opened!")

    page.wait_for_timeout(3000)

    input("\nLook at the page. Press Enter here once you've inspected it...")

    browser.close()