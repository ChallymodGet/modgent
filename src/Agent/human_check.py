import re


def _looks_like_human_check(url: str, title: str, body: str) -> bool:
    blob = f"{url} {title} {body}".lower()
    return any(
        part in blob
        for part in (
            "additional verification",
            "verify you are human",
            "just a moment",
            "ray id",
        )
    )


async def page_needs_human_check(page) -> bool:
    try:
        title = (await page.title()).lower()
        body = " ".join((await page.locator("body").inner_text()).split())[:800].lower()
    except Exception:
        return False
    return _looks_like_human_check(page.url or "", title, body)


async def _click_verify_checkbox(page) -> bool:
    """Clicks the Cloudflare checkbox inside its frame. Does not click Submit or Return home."""
    for frame in page.frames:
        frame_url = (frame.url or "").lower()
        if frame == page.main_frame:
            continue
        if not any(part in frame_url for part in ("cloudflare", "turnstile", "challenge-platform")):
            continue
        try:
            checkbox = frame.locator("input[type='checkbox']")
            if await checkbox.count() and await checkbox.first.is_visible():
                await checkbox.first.click(timeout=4000)
                return True
            label = frame.get_by_text(re.compile(r"verify you are human", re.I))
            if await label.count() and await label.first.is_visible():
                await label.first.click(timeout=4000)
                return True
        except Exception:
            continue

    try:
        widget = page.frame_locator(
            "iframe[src*='challenges.cloudflare.com'], iframe[title*='Cloudflare'], iframe[title*='challenge']"
        )
        checkbox = widget.locator("input[type='checkbox']")
        if await checkbox.count():
            await checkbox.first.click(timeout=4000)
            return True
        label = widget.get_by_text(re.compile(r"verify you are human", re.I))
        if await label.count():
            await label.first.click(timeout=4000)
            return True
    except Exception:
        pass

    try:
        box = page.get_by_role("checkbox", name=re.compile(r"verify you are human", re.I))
        if await box.count() and await box.first.is_visible():
            await box.first.click(timeout=4000)
            return True
    except Exception:
        pass
    return False


async def settle_human_check(page) -> bool:
    """
    If Indeed (or the company site) is showing Verify you are human, click the
    checkbox and wait for the real page. Returns True when a check was cleared.
    """
    if not await page_needs_human_check(page):
        return False

    print("Verification page is up. Clicking Verify you are human.")
    cleared = False
    for attempt in range(2):
        if attempt == 0 or await page_needs_human_check(page):
            await _click_verify_checkbox(page)
        for _ in range(12):
            await page.wait_for_timeout(1000)
            if not await page_needs_human_check(page):
                cleared = True
                break
        if cleared:
            print("Verification cleared.")
            return True
    print("The checkbox is still on screen.")
    return False
