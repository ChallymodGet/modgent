import re

from playwright.async_api import async_playwright
from src.Agent.form_filler import (
    application_scope,
    dismiss_overlays,
    page_asks_for_cover_letter,
    stage_cover_letter,
    _is_reviewed,
    fill_known_fields,
    focus_application,
    generate_and_store_answers,
    missing_resume_choice,
    prepare_application_documents,
    store_blockers,
    type_confirmed_answers,
    unanswered_required,
)
from src.Agent import session_registry
from src.Agent.human_check import settle_human_check
from src.api.config import settings
from src.api.models import update_job_status, Job
from sqlmodel import Session


# Indeed's off-site button, then the Apply button on the company site itself.
_INDEED_APPLY = (
    ("button", r"Apply on company site"),
    ("link", r"Apply on company site"),
    ("button", r"Apply on company website"),
    ("link", r"Apply on company website"),
    ("button", r"^Continue to application$"),
    ("link", r"^Continue to application$"),
    ("button", r"^Continue to company site$"),
    ("link", r"^Continue to company site$"),
)
_COMPANY_APPLY = (
    ("button", r"^Apply now$"),
    ("link", r"^Apply now$"),
    ("button", r"^Apply for this (job|position|role)$"),
    ("link", r"^Apply for this (job|position|role)$"),
    ("button", r"^Easy Apply$"),
    ("button", r"^Apply$"),
    ("link", r"^Apply$"),
)


async def _first_matching(page, pairs):
    for role, pattern in pairs:
        control = page.get_by_role(role, name=re.compile(pattern, re.I))
        try:
            count = await control.count()
        except Exception:
            continue
        for index in range(min(count, 6)):
            item = control.nth(index)
            try:
                if await item.is_visible():
                    return item
            except Exception:
                continue
    return None


async def _click_and_follow(context, page, control):
    """Clicks a control that may open a new tab or navigate the current one."""
    try:
        await control.scroll_into_view_if_needed(timeout=3000)
    except Exception:
        pass

    popup = None
    try:
        async with context.expect_page(timeout=8000) as new_page_info:
            await control.click(timeout=8000)
        popup = await new_page_info.value
    except Exception:
        popup = None

    if popup is not None:
        try:
            await popup.wait_for_url(re.compile(r"^(?!about:).+"), timeout=15000)
        except Exception:
            pass
        await wait_for_document(popup)
        print(f"Opened the application: {popup.url}")
        return popup

    await wait_for_document(page)
    return page


async def _application_form_open(page) -> bool:
    """True when the page is showing an application, not just the job posting."""
    scope = await application_scope(page)
    fields = scope.locator(
        "input:not([type='hidden']):not([type='search']):not([type='checkbox']):not([type='radio']), textarea, select"
    )
    visible = 0
    try:
        count = await fields.count()
    except Exception:
        return False
    for index in range(min(count, 15)):
        try:
            if await fields.nth(index).is_visible():
                visible += 1
                if visible >= 2:
                    return True
        except Exception:
            continue
    return False


async def wait_for_document(page, timeout_ms: int = 30000) -> None:
    """The page's own load event. domcontentloaded fires while the form is still blank."""
    try:
        await page.wait_for_load_state("load", timeout=timeout_ms)
    except Exception:
        pass


async def wait_for_form(page, timeout_ms: int = 30000) -> bool:
    """True once the application fields are actually on the page, including inside an embed."""
    waited = 0
    while waited <= timeout_ms:
        if await _application_form_open(page):
            return True
        await page.wait_for_timeout(500)
        waited += 500
    return False


async def wait_for_company_page(page, timeout_ms: int = 30000) -> None:
    """
    Indeed's Apply on company site stops on a redirect page first.
    Stay there until the employer page has replaced it and finished loading.
    """
    url = page.url or ""
    if "indeed.com" in url and "viewjob" not in url:
        try:
            await page.wait_for_url(re.compile(r"^(?!.*indeed\.com).+"), timeout=timeout_ms)
        except Exception:
            pass
    await wait_for_document(page)


async def _indeed_company_apply(page):
    """The Indeed button that leaves Indeed for the employer's own application."""
    control = await _first_matching(page, _INDEED_APPLY)
    if control is not None:
        return control
    fallback = page.locator("#indeedApplyButton")
    try:
        if await fallback.count() and await fallback.first.is_visible():
            label = " ".join((await fallback.first.inner_text()).split()).lower()
            if "company site" in label or "company website" in label:
                return fallback.first
    except Exception:
        return None
    return None


async def open_application_form(context, page, job_url):
    """
    Opens the posting and follows it through to the application form.
    On Indeed that means clicking Apply on company site, then Apply on the
    employer's site, and continuing there.
    """
    await page.goto(job_url, timeout=60000, wait_until="load")
    await wait_for_document(page)
    await settle_human_check(page)

    for _ in range(4):
        await settle_human_check(page)
        on_indeed = "indeed.com" in (page.url or "")
        if not on_indeed and await _application_form_open(page):
            break

        if on_indeed:
            control = await _indeed_company_apply(page)
            if control is None and "viewjob" not in (page.url or ""):
                control = await _first_matching(page, (
                    ("button", r"^Continue$"),
                    ("link", r"^Continue$"),
                ))
        else:
            control = await _first_matching(page, _COMPANY_APPLY)
        if control is None:
            if on_indeed and "viewjob" not in (page.url or ""):
                await wait_for_company_page(page)
                continue
            break

        try:
            label = " ".join((await control.inner_text()).split())
        except Exception:
            label = "Apply"
        print(f"Clicking '{label}'.")
        previous = page.url
        page = await _click_and_follow(context, page, control)
        await wait_for_company_page(page)
        if "indeed.com" not in (page.url or "") and page.url == previous and await _application_form_open(page):
            break

    await wait_for_company_page(page)
    return page


async def _footer_button(page, pattern: str):
    """
    A footer button inside the application dialog whose whole name matches.
    'Next' must not match a company link such as Nextiva, and the click must
    stay on the dialog instead of the page behind it.
    """
    dialog = page.locator("dialog[open], [role='dialog']")
    scope = page
    try:
        count = await dialog.count()
    except Exception:
        count = 0
    for index in range(count - 1, -1, -1):
        item = dialog.nth(index)
        try:
            if await item.is_visible():
                scope = item
                break
        except Exception:
            continue
    # Company sites often use a link for Next. The name still has to match exactly.
    for role in ("button", "link"):
        button = scope.get_by_role(role, name=re.compile(pattern, re.I))
        try:
            if await button.count() and await button.first.is_visible():
                return button.first
        except Exception:
            continue
    return None


async def advance_application(
    page,
    job: Job,
    candidate_summary: str,
    contact: dict,
    recurring_answers: dict,
    cv_path: str,
    session: Session,
    replay: bool = False,
    cv_name: str = "",
    cv_text: str = "",
) -> str:
    """
    Fills the open application until a required blank stops it, or until Review.

    `replay` types answers the user already confirmed before scanning again,
    then moves to the next page. Submit is never clicked.
    Returns "needs_you", "review", or "stopped".
    """
    await wait_for_company_page(page)
    await wait_for_form(page)

    for _ in range(8):
        await settle_human_check(page)
        await dismiss_overlays(page)
        form = await application_scope(page)
        if form is page:
            await wait_for_form(page, 5000)
            form = await application_scope(page)
        await focus_application(page, form)
        cover_path = None
        cover_blocker = None
        if await page_asks_for_cover_letter(form):
            try:
                cover_path, cover_blocker = stage_cover_letter(session, job, cv_text or candidate_summary)
            except Exception as e:
                print(f"Could not draft a cover letter: {e}")
        await prepare_application_documents(form, cv_path, cover_path, cv_name=cv_name)
        if replay:
            await type_confirmed_answers(form, job.job_id, session)
        await fill_known_fields(
            form,
            contact,
            recurring_answers,
            session=session,
            cv_path=cv_path,
            cv_name=cv_name,
        )
        await generate_and_store_answers(
            form,
            job.job_id,
            job.description,
            candidate_summary,
            session,
        )

        blockers = await unanswered_required(form)
        resume = await missing_resume_choice(page)
        if resume:
            blockers.append(resume)
        if cover_blocker:
            blockers.insert(0, cover_blocker)
        blockers = [item for item in blockers if not _is_reviewed(session, job.job_id, item["question"])]
        if blockers:
            print(f"\nWaiting on {len(blockers)} required field(s).")
            store_blockers(session, job.job_id, blockers)
            update_job_status(job.job_id, "Needs you")
            return "needs_you"

        submit_button = await _footer_button(form, r"^(Submit|Submit application|Apply Now)$")
        if submit_button is not None:
            print("\nReached the final page. Stopping before Submit.")
            update_job_status(job.job_id, "Pending Review")
            return "review"

        review_button = await _footer_button(form, r"^(Review|Review your application)$")
        if review_button is not None:
            print("\nClicking Review.")
            try:
                await review_button.click(timeout=5000)
                await page.wait_for_timeout(1200)
            except Exception as e:
                print(f"Review stayed on this page: {e}")
            await fill_known_fields(form, contact, recurring_answers, session=session, cv_path=cv_path, cv_name=cv_name)
            blockers = await unanswered_required(form)
            if blockers:
                store_blockers(session, job.job_id, blockers)
                update_job_status(job.job_id, "Needs you")
                return "needs_you"
            update_job_status(job.job_id, "Pending Review")
            return "review"

        next_button = await _footer_button(form, r"^(Next|Continue|Continue to next step)$")
        if next_button is None:
            print("\nNo Next or Review button in the application window. Paused.")
            update_job_status(job.job_id, "Pending Review")
            return "stopped"

        print("\nClicking Next.")
        try:
            await next_button.click(timeout=5000)
            await wait_for_document(page)
            await wait_for_form(page, 15000)
        except Exception as e:
            print(f"Could not move to the next step: {e}")
            blockers = await unanswered_required(form)
            if blockers:
                store_blockers(session, job.job_id, blockers)
            update_job_status(job.job_id, "Needs you")
            return "needs_you"
        replay = False

    update_job_status(job.job_id, "Pending Review")
    return "review"


async def apply_to_job(
    job_id: str,
    candidate_summary: str,
    contact: dict,
    recurring_answers: dict,
    cv_path: str,
    session: Session,
    cv_name: str = "",
    cv_text: str = "",
) -> str:
    """
    Opens a single job's application form and runs the asynchronous filling
    process. `contact`, `recurring_answers`, and `cv_path` all come from the
    candidate's Profile (editable via the UI) instead of hardcoded values.

    This function is called as a background task. It does NOT use input()
    and instead updates the database with progress.

    IMPORTANT: unlike a typical Playwright script, this does NOT close the
    browser when it's done pre-filling. The browser context is registered
    in `session_registry` so that once the human reviews/edits the AI
    drafted answers, those finalized answers can actually be typed into
    this SAME live page (see form_filler.apply_final_answers_to_page).
    Nothing is ever auto-submitted — the human always clicks Submit.
    """
    job = session.get(Job, job_id)
    if not job:
        print(f"Job {job_id} not found in database.")
        return

    print(f"\n{'='*60}")
    print(f"Opening application: {job.company} - {job.title}")
    print(f"{'='*60}")

    playwright = await async_playwright().start()
    try:
        context = await playwright.chromium.launch_persistent_context(
            user_data_dir=settings.browser_profile_path,
            headless=False,
            channel=settings.browser_channel,
            args=["--disable-blink-features=AutomationControlled"],
        )
    except Exception:
        await playwright.stop()
        raise

    page = context.pages[0] if context.pages else await context.new_page()
    try:
        target_page = await open_application_form(context, page, job.url)
    except Exception:
        await context.close()
        await playwright.stop()
        raise

    try:
        outcome = await advance_application(
            target_page,
            job,
            candidate_summary,
            contact,
            recurring_answers,
            cv_path,
            session,
            cv_name=cv_name,
            cv_text=cv_text,
        )
    except Exception:
        outcome = "stopped"
        await session_registry.register_session(job_id, playwright, context, target_page)
        raise

    print("\nForm has been pre-filled where possible.")
    await session_registry.register_session(job_id, playwright, context, target_page)
    return outcome
