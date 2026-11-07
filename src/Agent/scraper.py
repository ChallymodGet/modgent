from playwright.async_api import async_playwright
import asyncio
import re
from typing import List, Dict, Optional
from urllib.parse import quote_plus
from src.Agent.human_check import page_needs_human_check, settle_human_check
from src.api.config import settings

def extract_job_id(url: Optional[str]) -> Optional[str]:
    if url is None:
        return None
    match = re.search(r'-(\d+)\?', url)
    if match:
        return match.group(1)
    return None

async def close_login_popup(page):
    close_button_selectors = [
        "button[aria-label='Dismiss']",
        "button.modal__dismiss",
        "button[data-tracking-control-name='public_jobs_contextual-sign-in-modal_modal_dismiss']",
        ".contextual-sign-in-modal__modal-dismiss",
    ]

    for selector in close_button_selectors:
        try:
            button = page.locator(selector)
            if await button.count() > 0:
                await button.first.click(timeout=3000)
                print(f"Closed popup using selector: {selector}")
                await page.wait_for_timeout(500)
                return
        except Exception:
            continue

    try:
        overlay = page.locator(".modal__overlay")
        if await overlay.count() > 0:
            await overlay.first.click(position={"x": 10, "y": 10}, timeout=3000)
            print("Closed login popup (clicked outside).")
            await page.wait_for_timeout(500)
    except Exception:
        pass

async def open_browser(playwright, *, headless=True, user_data_dir=None, offscreen=False):
    """
    Persistent Edge context. Discovery passes the signed-out search profile.
    Applying to a job uses the saved login profile in a visible window.
    """
    args = ["--disable-blink-features=AutomationControlled"]
    if offscreen:
        args += ["--window-position=-2400,-2400", "--window-size=1280,900"]
    kwargs = dict(
        user_data_dir=user_data_dir or settings.browser_profile_path,
        headless=headless,
        channel=settings.browser_channel,
        args=args,
    )
    if not headless:
        kwargs["ignore_default_args"] = ["--enable-automation"]
    context = await playwright.chromium.launch_persistent_context(**kwargs)
    page = context.pages[0] if context.pages else await context.new_page()
    return context, page


async def _signal(on_progress, *, count=None, message=None, phase=None):
    if on_progress is not None:
        await on_progress({"count": count, "message": message, "phase": phase})


async def _tick(on_progress, count: int):
    await _signal(on_progress, count=count)


async def _body_sample(page) -> str:
    try:
        text = await page.locator("body").inner_text()
    except Exception:
        return ""
    return " ".join(text.split())[:600].lower()


def _linkedin_blocked(url: str, title: str, body: str) -> bool:
    blob = f"{url} {title} {body}"
    return any(
        part in blob
        for part in ("checkpoint", "authwall", "make sure it’s really you", "make sure it's really you")
    )


def _indeed_blocked(url: str, title: str, body: str) -> bool:
    blob = f"{url} {title} {body}"
    return any(
        part in blob
        for part in ("blocked", "just a moment", "additional verification", "ray id", "verify you are human")
    )


async def _first_selector(page, selectors):
    for selector in selectors:
        if await page.locator(selector).count() > 0:
            return selector
    return None


async def _wait_for_cards(page, selectors, timeout_s, on_progress, board, blocked_message):
    announced = False
    for _ in range(timeout_s):
        found = await _first_selector(page, selectors)
        if found:
            return found
        url = page.url.lower()
        title = (await page.title()).lower()
        body = await _body_sample(page)
        blocked = _linkedin_blocked(url, title, body) if board == "LinkedIn" else _indeed_blocked(url, title, body)
        if blocked and not announced:
            announced = True
            print(f"{board} is showing a human check.")
            still_blocked = True
            if board == "Indeed":
                await settle_human_check(page)
                still_blocked = await page_needs_human_check(page)
            if still_blocked:
                await _signal(on_progress, message=blocked_message, phase="check")
        await page.wait_for_timeout(1000)
    return None


async def _collect_linkedin_member(page, max_jobs: int, on_progress) -> List[Dict]:
    """Signed-in LinkedIn results use job-card-container, not the public base-card."""
    jobs = []
    cards = page.locator("div.job-card-container")
    count = await cards.count()
    print(f"Found {count} signed-in job cards.")
    await _tick(on_progress, 0)

    for i in range(min(count, max_jobs)):
        card = cards.nth(i)
        try:
            link = card.locator("a.job-card-container__link, a.job-card-list__title").first
            raw_title = (await link.inner_text()).strip()
            title = next((line.strip() for line in raw_title.splitlines() if line.strip()), raw_title)
            job_url = await link.get_attribute("href")
            job_id = await card.get_attribute("data-job-id")
            if not job_id and job_url:
                match = re.search(r"/jobs/view/(\d+)", job_url)
                job_id = match.group(1) if match else extract_job_id(job_url)

            try:
                company = (await card.locator(
                    ".artdeco-entity-lockup__subtitle, .job-card-container__primary-description"
                ).first.inner_text()).strip()
            except Exception:
                company = "Unknown"
            try:
                location_text = (await card.locator(".job-card-container__metadata-item").first.inner_text()).strip()
            except Exception:
                location_text = "Unknown"

            await card.click(timeout=10000, force=True)
            description_locator = page.locator("#job-details, .jobs-description__content, .jobs-box__html-content")
            await description_locator.first.wait_for(state="visible", timeout=10000)
            description = (await description_locator.first.inner_text()).strip()

            jobs.append({
                "title": title,
                "company": company,
                "location": location_text,
                "description": description,
                "url": job_url,
                "job_id": job_id,
                "source": "LinkedIn",
            })
            print("Job successfully added!")
            await _tick(on_progress, len(jobs))
        except Exception as e:
            print(f"ERROR processing job {i + 1}: {e}")

    return jobs


async def search_linkedin(keywords: str, location: str, max_jobs: int = 15, on_progress=None) -> List[Dict]:
    jobs = []
    search_url = (
        "https://www.linkedin.com/jobs/search/"
        f"?keywords={quote_plus(keywords)}&location={quote_plus(location)}"
    )
    linkedin_cards = ["div.base-card", "div.job-card-container"]
    check_message = "LinkedIn needs you to confirm it's you. Finish that in the browser window."

    async with async_playwright() as p:
        # Public listings. The saved apply login is currently stuck on a
        # verification challenge, which is why this board was returning 0.
        context, page = await open_browser(
            p, headless=True, user_data_dir=settings.browser_linkedin_profile_path,
        )

        await page.goto(search_url, timeout=60000, wait_until="domcontentloaded")
        print("LinkedIn Jobs opened!")

        await close_login_popup(page)
        selector = await _wait_for_cards(page, linkedin_cards, 20, on_progress, "LinkedIn", check_message)

        if selector is None:
            url = page.url.lower()
            title = (await page.title()).lower()
            body = await _body_sample(page)
            if _linkedin_blocked(url, title, body):
                print("LinkedIn asked for a human check. Opening a visible window.")
                await context.close()
                context, page = await open_browser(p, headless=False, user_data_dir=settings.browser_profile_path)
                await page.goto(search_url, timeout=60000, wait_until="domcontentloaded")
                selector = await _wait_for_cards(page, linkedin_cards, 180, on_progress, "LinkedIn", check_message)

        if selector is None:
            print(f"LinkedIn returned no job cards. URL: {page.url}")
            await _signal(on_progress, count=0, message="LinkedIn returned no listings.")
            await context.close()
            return jobs

        if selector == "div.job-card-container":
            jobs = await _collect_linkedin_member(page, max_jobs, on_progress)
            await context.close()
            return jobs

        job_cards = page.locator("div.base-card")
        count = await job_cards.count()
        print(f"Found {count} job cards.")
        await _tick(on_progress, 0)

        for i in range(min(count, max_jobs)):
            print(f"\nProcessing job {i + 1}...")
            card = job_cards.nth(i)

            try:
                raw_title = (await card.locator("h3").inner_text()).strip()
                title_lines = [line.strip() for line in raw_title.splitlines() if line.strip()]
                title = title_lines[0] if title_lines else raw_title
                company = (await card.locator("h4").inner_text()).strip()
                location_text = (await card.locator(".job-search-card__location").inner_text()).strip()

                job_url = await card.locator("a.base-card__full-link").get_attribute("href")
                job_id = extract_job_id(job_url)

                print(f"Title found: {title}")
                print(f"Company found: {company}")
                print(f"Location found: {location_text}")
                print(f"Job ID: {job_id}")

                await card.click(timeout=10000, force=True)
                print("Job clicked. Waiting for details to load...")

                detail_title_locator = page.locator(
                    ".job-details-jobs-unified-top-card__job-title, .top-card-layout__title"
                )

                try:
                    await detail_title_locator.first.wait_for(state="visible", timeout=10000)
                except Exception:
                    pass

                matched = False
                for _ in range(10):
                    try:
                        current_detail_title = (await detail_title_locator.first.inner_text()).strip()
                    except Exception:
                        current_detail_title = ""

                    if (title.lower() in current_detail_title.lower()
                            or current_detail_title.lower() in title.lower()):
                        matched = True
                        break

                    await page.wait_for_timeout(300)

                if not matched:
                    print("Warning: detail panel title did not confirm match — description may be stale.")

                description_locator = page.locator(".show-more-less-html__markup")
                await description_locator.first.wait_for(state="visible", timeout=10000)
                await page.wait_for_timeout(500)

                description = (await description_locator.first.inner_text()).strip()

                jobs.append({
                    "title": title,
                    "company": company,
                    "location": location_text,
                    "description": description,
                    "url": job_url,
                    "job_id": job_id,
                    "source": "LinkedIn"
                })

                print("Job successfully added!")
                await _tick(on_progress, len(jobs))

            except Exception as e:
                print(f"ERROR processing job {i + 1}: {e}")

        await context.close()

    return jobs

async def search_indeed(keywords: str, location: str, max_jobs: int = 15, on_progress=None) -> List[Dict]:
    jobs = []
    search_url = (
        "https://www.indeed.com/jobs"
        f"?q={quote_plus(keywords)}&l={quote_plus(location)}"
    )
    indeed_cards = ["div.job_seen_beacon", "div.cardOutline"]
    check_message = "Indeed is asking you to verify you're human. Tick the box in the browser window."

    async with async_playwright() as p:
        # Headless Edge is hard-blocked by Indeed. A real window, kept off
        # screen, can pass on its own. If a checkbox appears, bring it forward.
        context, page = await open_browser(
            p,
            headless=False,
            offscreen=True,
            user_data_dir=settings.browser_search_profile_path,
        )

        await page.goto(search_url, timeout=60000, wait_until="domcontentloaded")
        print("Indeed opened!")
        selector = await _wait_for_cards(page, indeed_cards, 12, on_progress, "Indeed", check_message)

        if selector is None:
            print("Indeed needs a visible human check.")
            await _signal(on_progress, message=check_message, phase="check")
            await context.close()
            context, page = await open_browser(
                p, headless=False, user_data_dir=settings.browser_search_profile_path,
            )
            await page.goto(search_url, timeout=60000, wait_until="domcontentloaded")
            selector = await _wait_for_cards(page, indeed_cards, 180, on_progress, "Indeed", check_message)

        if selector is None:
            print(f"Indeed returned no job cards. URL: {page.url}")
            await _signal(
                on_progress,
                count=0,
                message="Indeed returned no listings. The human check was not finished.",
            )
            await context.close()
            return jobs

        job_cards = page.locator(selector)
        count = await job_cards.count()
        print(f"Found {count} job cards.")
        await _tick(on_progress, 0)

        for i in range(min(count, max_jobs)):
            print(f"\nProcessing job {i + 1}...")
            card = job_cards.nth(i)

            try:
                title_link = card.locator("h2.jobTitle a, h3.jobTitle a, a.jcs-JobTitle").first
                title = (await title_link.inner_text()).strip()
                job_id = await title_link.get_attribute("data-jk")
                job_url = f"https://www.indeed.com/viewjob?jk={job_id}"

                try:
                    company = (await card.locator("[data-testid='company-name']").inner_text()).strip()
                except Exception:
                    company = "Unknown"

                try:
                    location_text = (await card.locator("[data-testid='text-location']").inner_text()).strip()
                except Exception:
                    location_text = "Unknown"

                print(f"Title found: {title}")
                print(f"Company found: {company}")
                print(f"Location found: {location_text}")
                print(f"Job ID: {job_id}")

                await title_link.click(timeout=10000, force=True)
                print("Job clicked. Waiting for details to load...")

                try:
                    await page.wait_for_timeout(2000)
                    description_selectors = [
                        "#jobDescriptionText",
                        ".job-description-container",
                        "[data-testid='job-description']",
                        "div.job-description"
                    ]

                    description = ""
                    for selector in description_selectors:
                        loc = page.locator(selector).first
                        if await loc.is_visible(timeout=2000):
                            description = (await loc.inner_text()).strip()
                            break

                    if not description:
                        print("  Standard selectors failed. Trying brute-force text search...")
                        divs = page.locator("div")
                        best_div = ""
                        max_len = 0
                        div_count = await divs.count()
                        for i in range(min(div_count, 100)):
                            text = await divs.nth(i).inner_text()
                            if len(text) > 200 and ("description" in text.lower() or "about the job" in text.lower()):
                                if len(text) > max_len:
                                    max_len = len(text)
                                    best_div = text
                        description = best_div.strip()

                    if not description:
                        raise Exception("No description text found using any strategy")

                    await page.wait_for_timeout(500)
                except Exception as e:
                    print(f"  Description extraction failed: {e}")
                    description = ""

                jobs.append({
                    "title": title,
                    "company": company,
                    "location": location_text,
                    "description": description,
                    "url": job_url,
                    "job_id": job_id,
                    "source": "Indeed"
                })

                print("Job successfully added!")
                await _tick(on_progress, len(jobs))

            except Exception as e:
                print(f"ERROR processing job {i + 1}: {e}")

        await context.close()

    return jobs

def wellfound_role_slugs(keywords: str) -> List[str]:
    """
    Wellfound browses by role page (/role/product-designer), not free text.
    Each comma-separated target role becomes its own slug.
    """
    slugs = []
    for role in keywords.split(","):
        slug = re.sub(r"[^a-z0-9]+", "-", role.lower()).strip("-")
        if slug and slug not in slugs:
            slugs.append(slug)
    return slugs


async def search_wellfound(keywords: str, location: str, max_jobs: int = 15, on_progress=None) -> List[Dict]:
    jobs = []

    async with async_playwright() as p:
        context, page = await open_browser(p, user_data_dir=settings.browser_wellfound_profile_path)

        collected_urls = []
        collected_titles = []

        for role_slug in wellfound_role_slugs(keywords):
            if len(collected_urls) >= max_jobs:
                break
            search_url = f"https://wellfound.com/role/{role_slug}"
            try:
                await page.goto(search_url, timeout=60000, wait_until="domcontentloaded")
            except Exception as e:
                print(f"Could not open Wellfound role {role_slug}: {e}")
                continue
            print(f"Wellfound opened: {role_slug}")

            await page.wait_for_timeout(4000)
            job_links = page.locator("a[href^='/jobs/']")
            link_count = await job_links.count()
            print(f"Found {link_count} job links.")
            await _tick(on_progress, 0)

            for i in range(link_count):
                if len(collected_urls) >= max_jobs:
                    break
                href = await job_links.nth(i).get_attribute("href")
                title_text = (await job_links.nth(i).inner_text()).strip()

                if href and href not in collected_urls:
                    collected_urls.append(href)
                    collected_titles.append(title_text)

        print(f"Collected {len(collected_urls)} unique job links.")

        for i, relative_url in enumerate(collected_urls):
            print(f"\nProcessing job {i + 1}...")
            full_url = f"https://wellfound.com{relative_url}"

            try:
                detail_page = await context.new_page()
                await detail_page.goto(full_url, timeout=15000)
                await detail_page.wait_for_timeout(1500)

                title = collected_titles[i]

                try:
                    header_text = (await detail_page.locator("[data-testid='startup-header']").inner_text()).strip()
                    company = header_text.split("\n")[0].strip()
                except Exception as e:
                    print(f"  Company extraction failed: {e}")
                    company = "Unknown"

                try:
                    location_locator = detail_page.locator("text=Job Location").locator("..")
                    await location_locator.wait_for(state="visible", timeout=3000)
                    raw_location = (await location_locator.inner_text()).strip()
                    location_text = raw_location.replace("Job Location", "").strip()
                except Exception:
                    location_text = "Not specified"

                try:
                    description = (await detail_page.locator("text=About the job").locator("..").inner_text()).strip()
                except Exception as e:
                    print(f"  Description extraction failed: {e}")
                    description = ""

                job_id_match = re.search(r'/jobs/(\d+)-', relative_url)
                job_id = job_id_match.group(1) if job_id_match else relative_url

                print(f"Title found: {title}")
                print(f"Company found: {company}")
                print(f"Location found: {location_text}")
                print(f"Description length: {len(description)}")
                print(f"Job ID: {job_id}")

                jobs.append({
                    "title": title,
                    "company": company,
                    "location": location_text,
                    "description": description,
                    "url": full_url,
                    "job_id": job_id,
                    "source": "Wellfound"
                })

                print("Job successfully added!")
                await _tick(on_progress, len(jobs))
                await detail_page.close()

            except Exception as e:
                print(f"ERROR processing job {i + 1}: {e}")

        await context.close()

    return jobs

async def search_all_boards(keywords: str, location: str, max_jobs_per_board: int = 15, on_progress=None) -> List[Dict]:
    all_jobs = []
    boards = ["LinkedIn", "Indeed", "Wellfound"]
    state = {name: "waiting" for name in boards}
    counts = {name: 0 for name in boards}

    async def emit(board: str, phase: str, message: str):
        state[board] = phase
        if on_progress is None:
            return
        await on_progress({
            "board": board,
            "phase": phase,
            "found": sum(counts.values()),
            "message": message,
            "boards": dict(state),
            "counts": dict(counts),
        })

    async def track(board: str):
        async def _on_event(event):
            if isinstance(event, int):
                event = {"count": event}
            count = event.get("count")
            if count is not None:
                counts[board] = count
            phase = event.get("phase") or "reading"
            shown = counts[board]
            message = event.get("message") or (
                f"Reading {board} · {shown} listing{'s' if shown != 1 else ''}"
            )
            await emit(board, phase, message)
        return _on_event

    searches = {
        "LinkedIn": search_linkedin,
        "Indeed": search_indeed,
        "Wellfound": search_wellfound,
    }

    async def run(board: str) -> List[Dict]:
        # Each board uses its own browser profile, so all three run at once.
        # One board failing must not throw away the others' results.
        print(f"\n=== Searching {board} ===")
        await emit(board, "opening", f"Opening {board}")
        try:
            found = await searches[board](
                keywords, location, max_jobs_per_board, on_progress=await track(board),
            )
        except Exception as e:
            print(f"{board} search failed: {e}")
            await emit(board, "failed", f"{board} could not be searched")
            return []
        counts[board] = len(found)
        await emit(board, "done", f"{board} done · {len(found)} listings")
        return found

    for found in await asyncio.gather(*(run(board) for board in boards)):
        all_jobs.extend(found)

    return all_jobs
