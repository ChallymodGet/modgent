from playwright.sync_api import sync_playwright

SEARCH_URL = "https://my.greenhouse.io/jobs/search?query=product%20designer"
MAX_JOBS_TO_CHECK = 9


def close_modal(page):
    close_button = page.locator("button[aria-label='Close'], button[aria-label='Dismiss']")
    try:
        close_button.first.click(timeout=3000, force=True)
    except Exception:
        page.keyboard.press("Escape")
    page.wait_for_timeout(500)


with sync_playwright() as p:
    browser = p.chromium.launch(headless=False, channel="msedge")
    page = browser.new_page()
    page.goto(SEARCH_URL)

    page.wait_for_timeout(3000)

    print(f"Checking up to {MAX_JOBS_TO_CHECK} job postings for open-ended questions...\n")

    cards = page.locator("a[href*='/jobs/']")
    card_count = min(cards.count(), MAX_JOBS_TO_CHECK)

    for i in range(card_count):
        try:
            card = cards.nth(i)
            card_text = card.inner_text().strip().split("\n")[0][:50]

            card.click(timeout=5000, force=True)
            page.wait_for_timeout(1500)

            textareas = page.locator("textarea")
            count = textareas.count()

            visible_count = 0
            for j in range(count):
                try:
                    if textareas.nth(j).is_visible():
                        visible_count += 1
                except Exception:
                    continue

            print(f"  '{card_text}' -> {visible_count} open-ended question(s)")

            close_modal(page)

        except Exception as e:
            print(f"  Error on card {i}: {e}")
            close_modal(page)

    input("\nDone checking. Press Enter to close...")
    browser.close()