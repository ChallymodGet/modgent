from playwright.sync_api import sync_playwright
import os

def check_session():
    # Use the same persistent directory as application_runner.py
    user_data_dir = os.path.join(os.getcwd(), "browser_profile", "app_session")

    print(f"Checking session in: {user_data_dir}")

    with sync_playwright() as p:
        # Launch the persistent context
        context = p.chromium.launch_persistent_context(
            user_data_dir,
            headless=False,
            channel="msedge",
            args=["--disable-blink-features=AutomationControlled"]
        )
        page = context.pages[0] if context.pages else context.new_page()

        print("Navigating to Indeed...")
        try:
            page.goto("https://www.indeed.com", timeout=60000)
            page.wait_for_timeout(3000)

            # Check for signs of being logged in
            # We look for common "logged in" indicators like a profile icon or "Sign Out" text
            is_logged_in = False

            # Strategy 1: Look for "Sign Out" or "My Account"
            if page.get_by_text("Sign Out", exact=False).count() > 0 or \
               page.get_by_text("My Account", exact=False).count() > 0:
                is_logged_in = True

            # Strategy 2: Check for the profile icon/link
            if page.locator("a[href*='/profile']").count() > 0:
                is_logged_in = True

            if is_logged_in:
                print("\n✅ SUCCESS: You are still logged in!")
            else:
                print("\n❌ FAILED: Session not found. You are on the login page.")

        except Exception as e:
            print(f"An error occurred while checking session: {e}")

        context.close()

if __name__ == "__main__":
    check_session()
