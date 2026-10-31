from datetime import datetime, timezone
import re
from typing import List, Dict, Tuple, Optional
from src.api.models import ApplicationAnswer, LearnedAnswer
from sqlmodel import Session, select

async def get_field_identifier(page, input_element):
    """
    Tries several ways to figure out what a form field is asking for.
    Includes advanced context searching (parents and siblings) for modern web apps.
    """
    identifiers = []

    # 1. Standard Attributes
    try:
        for attr in ["placeholder", "aria-label", "name", "id"]:
            val = await input_element.get_attribute(attr)
            if val:
                identifiers.append(val)
    except Exception:
        pass

    # 2. Associated <label> tag (via 'for' attribute)
    try:
        id_attr = await input_element.get_attribute("id")
        if id_attr:
            label = page.locator(f"label[for='{id_attr}']")
            if await label.count() > 0:
                identifiers.append(await label.first.inner_text())
    except Exception:
        pass

    # 3. Sibling context: Look for text in the element immediately before the input
    try:
        previous_sibling = input_element.locator("xpath=preceding-sibling::*[1]")
        if await previous_sibling.count() > 0:
            identifiers.append(await previous_sibling.first.inner_text())
    except Exception:
        pass

    # 4. Parent context: Look for text in the immediate parent wrapper
    try:
        parent = input_element.locator("xpath=..")
        if await parent.count() > 0:
            parent_text = " ".join((await parent.first.inner_text()).split())
            # A short wrapper is the question. The whole dialog is not.
            if parent_text and len(parent_text) <= 240:
                identifiers.append(parent_text)
    except Exception:
        pass

    # 5. Data attributes (common in custom frameworks)
    try:
        for data_attr in ["data-label", "data-field", "data-name"]:
            val = await input_element.get_attribute(data_attr)
            if val:
                identifiers.append(val)
    except Exception:
        pass

    return " ".join(identifiers).lower()


def _has_word(text: str, *words: str) -> bool:
    return any(re.search(rf"\b{re.escape(word)}\b", text) for word in words)


def is_protected_field(field_text: str) -> bool:
    """
    Checks whether a field's identifier contains any EEO/demographic language.
    """
    protected_keywords = [
        "race", "ethnicity", "ethnic", "gender", "sex assigned",
        "sexual orientation", "disability", "veteran", "pronoun",
        "demographic", "self-identif", "national origin", "voluntary"
    ]
    for keyword in protected_keywords:
        if keyword in field_text:
            return True
    return False


def match_field_to_value(field_text: str, contact: Dict) -> Optional[str]:
    """
    Matches field text to contact information.
    """
    field_text = field_text.replace("_", " ").replace("-", " ")
    if is_protected_field(field_text):
        return None

    if "resume" in field_text or _has_word(field_text, "cv"):
        return "__UPLOAD_CV__"

    if "email" in field_text:
        return contact.get("email")

    # Whole words only. "tell" contains "tel" and was being filled with the phone number.
    if _has_word(field_text, "phone", "mobile", "telephone", "tel"):
        return contact.get("phone")

    if "linkedin" in field_text:
        return contact.get("linkedin_url")

    if "portfolio" in field_text or "website" in field_text or "behance" in field_text:
        return contact.get("portfolio_url")

    if "first name" in field_text or "firstname" in field_text:
        name_parts = contact.get("name", "").split()
        return name_parts[0] if name_parts else None

    if "last name" in field_text or "lastname" in field_text:
        name_parts = contact.get("name", "").split()
        return name_parts[-1] if len(name_parts) > 1 else None

    if "full name" in field_text or (field_text.strip() == "name"):
        return contact.get("name")

    if _has_word(field_text, "country"):
        return contact.get("country")

    if "location" in field_text or "city" in field_text:
        return contact.get("location")

    if "state" in field_text or "province" in field_text or "region" in field_text:
        return contact.get("location")

    return None


def question_key(text: str) -> str:
    """Stable key for 'is this the same question?' — case and spacing ignored."""
    return " ".join((text or "").lower().split())[:400]


def question_label(text: str) -> str:
    return " ".join((text or "").split())[:180]


def questions_match(left: str, right: str) -> bool:
    """True when two labels are the same question, even if one is a shorter slice."""
    a, b = question_key(left), question_key(right)
    if not a or not b:
        return False
    if a == b:
        return True
    return len(a) >= 12 and len(b) >= 12 and (a in b or b in a)


def _find_application_answer(session: Session, job_id: str, question: str):
    rows = session.exec(select(ApplicationAnswer).where(ApplicationAnswer.job_id == job_id)).all()
    for row in rows:
        if questions_match(row.question, question):
            return row
    return None


def upsert_application_question(
    session: Session,
    job_id: str,
    question: str,
    draft: Optional[str] = None,
    choices: Optional[List[str]] = None,
    kind: Optional[str] = None,
):
    """
    One row per question per job. A later pass can add the choice list
    without wiping a draft that was already written.
    """
    choice_text = "\n".join(choice.strip() for choice in (choices or []) if choice and choice.strip()) or None
    row = _find_application_answer(session, job_id, question)
    if row:
        if choices is not None:
            row.choices = choice_text
        if kind:
            row.kind = kind
        if draft and not (row.draft_answer or "").strip():
            row.draft_answer = draft
        session.add(row)
        return row

    row = ApplicationAnswer(
        job_id=job_id,
        question=question_label(question) or question[:180],
        draft_answer=draft or "",
        choices=choice_text,
        kind=kind,
        is_reviewed=False,
    )
    session.add(row)
    return row


def find_learned_answer(field_text: str, learned: Dict[str, str]) -> Optional[str]:
    """
    Looks up an answer the user previously typed for this question.
    The stored key is often a shorter slice of the long field identifier,
    so a contained match counts when both sides are specific enough.
    """
    if not field_text or is_protected_field(field_text) or not learned:
        return None
    key = question_key(field_text)
    if key in learned:
        return learned[key]
    for stored, answer in learned.items():
        if len(stored) < 12 or len(key) < 12:
            continue
        if stored in key or key in stored:
            return answer
    return None


def load_learned_map(session: Optional[Session]) -> Dict[str, str]:
    if session is None:
        return {}
    rows = session.exec(select(LearnedAnswer)).all()
    return {row.question_key: row.answer for row in rows}


def remember_answer(session: Session, question: str, answer: str) -> bool:
    """
    Saves a user-provided answer for reuse. Protected questions and blanks
    are ignored. Returns True when a new answer was stored or an old one changed.
    """
    cleaned = (answer or "").strip()
    label = question_label(question)
    key = question_key(question)
    if not cleaned or len(key) < 3 or not label or is_protected_field(question):
        return False

    existing = session.exec(select(LearnedAnswer).where(LearnedAnswer.question_key == key)).first()
    if existing:
        if existing.answer.strip() == cleaned:
            return False
        existing.answer = cleaned
        existing.question = label
        existing.updated_at = datetime.now(timezone.utc)
        session.add(existing)
        return True

    session.add(LearnedAnswer(
        question_key=key,
        question=label,
        answer=cleaned,
        updated_at=datetime.now(timezone.utc),
    ))
    return True


def desired_field_value(field_text: str, contact: Dict, recurring_answers: Optional[Dict], learned: Dict[str, str]) -> Optional[str]:
    """Contact details, then the saved logistics answers, then anything the user taught the agent."""
    if is_protected_field(field_text):
        return None
    value = match_field_to_value(field_text, contact)
    if value and value != "__UPLOAD_CV__":
        return value
    if recurring_answers:
        recurring = match_recurring_question(field_text, recurring_answers)
        if recurring:
            return recurring
    return find_learned_answer(field_text, learned)


def match_recurring_question(field_text: str, recurring_answers: Dict) -> Optional[str]:
    """
    Matches field text to pre-filled logistics answers.
    """
    if "work eligib" in field_text or "authorized to work" in field_text or "legally eligible" in field_text:
        return recurring_answers.get("work_authorization")

    if "sponsorship" in field_text or "sponsor" in field_text:
        return recurring_answers.get("sponsorship_required")

    if "how did you hear" in field_text or "how did you find" in field_text:
        return recurring_answers.get("how_heard")

    if "non-compete" in field_text or "noncompete" in field_text:
        return recurring_answers.get("non_compete")

    if "relocate" in field_text or "relocation" in field_text:
        return recurring_answers.get("willing_to_relocate")

    if "experience" in field_text or "years of exp" in field_text or "years experience" in field_text:
        return recurring_answers.get("years_experience")

    if "salary" in field_text or "compensation" in field_text or "expected salary" in field_text:
        return recurring_answers.get("salary_expectation")

    return None


async def select_dropdown_option(page, combobox_element, desired_answer):
    """
    Handles react-select style dropdowns.
    """
    await combobox_element.click()
    await page.wait_for_timeout(500)
    named = page.get_by_role("option", name=re.compile(rf"^{re.escape(desired_answer)}$", re.I))
    try:
        if await named.count() and await named.first.is_visible():
            await named.first.click()
            return True
    except Exception:
        pass
    options = page.locator("[class*='select__option'], [role='option']")
    option_count = await options.count()
    desired_lower = desired_answer.lower()

    for i in range(option_count):
        option_text = (await options.nth(i).inner_text()).strip()
        if option_text.lower() == desired_lower:
            await options.nth(i).click()
            return True

    for i in range(option_count):
        option_text = (await options.nth(i).inner_text()).strip()
        if option_text.lower().startswith(desired_lower):
            await options.nth(i).click()
            return True

    owner = page if hasattr(page, "keyboard") else page.page
    await owner.keyboard.press("Escape")
    return False


async def find_open_ended_questions(page) -> List[Tuple]:
    """
    Finds textarea elements for open-ended questions.
    """
    questions = []
    textareas = page.locator("textarea")
    count = await textareas.count()
    for i in range(count):
        textarea = textareas.nth(i)
        try:
            if not await textarea.is_visible():
                continue
            question_text = await get_field_identifier(page, textarea)
            if question_text and not is_protected_field(question_text):
                questions.append((textarea, question_text))
        except Exception:
            continue
    return questions


async def generate_and_store_answers(page, job_id: str, job_description: str, candidate_summary: str, session: Session):
    """
    Phase 1 of the application: Find open-ended questions and generate AI drafts.
    Replaces the old review_and_fill_open_ended_questions which used input().
    """
    from src.Agent.answer_generator import generate_application_answer

    questions = await find_open_ended_questions(page)
    if not questions:
        print("\nNo open-ended questions found on this page.")
        return []

    print(f"\nFound {len(questions)} open-ended question(s). Generating drafts...")
    learned = load_learned_map(session)

    stored_answers = []
    for textarea, question_text in questions:
        remembered = find_learned_answer(question_text, learned)
        if remembered:
            draft = remembered
            try:
                await textarea.fill(remembered)
            except Exception as e:
                print(f"Could not type a saved answer: {e}")
        else:
            existing = _find_application_answer(session, job_id, question_text)
            if existing and (existing.draft_answer or "").strip():
                draft = existing.draft_answer
            else:
                draft = generate_application_answer(question_text, {"description": job_description}, candidate_summary)

        if draft:
            answer = upsert_application_question(session, job_id, question_text, draft=draft)
            stored_answers.append(answer)
            label = "Reused saved answer" if remembered else "Generated draft"
            print(f"{label} for: {question_text[:50]}...")
        else:
            print(f"Could not generate draft for: {question_text[:50]}...")

    session.commit()
    return stored_answers


async def apply_final_answers_to_page(page, answered_items: List[Tuple[str, str]]) -> Dict[str, List[str]]:
    """
    Phase 2 of the application: types the human-reviewed, finalized answers
    into the SAME live page the AI drafts were generated from. This never
    clicks Submit — the human always does that themselves once they're happy
    with what's on screen.

    `answered_items` is a list of (question_text, final_answer) tuples,
    matched by re-locating the open-ended question textareas currently on
    the page (their identifying text was stored alongside the draft).
    """
    questions_on_page = await find_open_ended_questions(page)

    applied = []
    not_found = []

    for question_text, final_answer in answered_items:
        match = None
        for textarea, page_question_text in questions_on_page:
            if page_question_text.strip() == question_text.strip():
                match = textarea
                break

        if match is None:
            for textarea, page_question_text in questions_on_page:
                a, b = page_question_text.strip().lower(), question_text.strip().lower()
                if a and b and (a in b or b in a):
                    match = textarea
                    break

        if match is not None:
            try:
                await match.fill(final_answer)
                applied.append(question_text)
            except Exception:
                not_found.append(question_text)
        else:
            not_found.append(question_text)

    await _apply_text_answers(page, answered_items, applied)
    await _apply_radio_answers(page, answered_items, applied)
    await _apply_select_answers(page, answered_items, applied)
    await _apply_combobox_answers(page, answered_items, applied)
    await _apply_checkbox_answers(page, answered_items, applied)

    return {"applied": applied, "not_found": not_found}


async def _read_control_value(element) -> str:
    try:
        tag = await element.evaluate("el => el.tagName")
    except Exception:
        return ""
    if tag == "SELECT":
        try:
            selected = element.locator("option:checked")
            if await selected.count() == 0:
                return ""
            return (await selected.first.inner_text()).strip()
        except Exception:
            return ""
    try:
        return (await element.input_value()).strip()
    except Exception:
        return ""


async def select_native_option(select_element, desired_answer: str) -> bool:
    desired = desired_answer.strip().lower()
    if not desired:
        return False
    options = select_element.locator("option")
    count = await options.count()
    labels = []
    for i in range(count):
        text = (await options.nth(i).inner_text()).strip()
        if text:
            labels.append(text)
    for text in labels:
        if text.lower() == desired:
            await select_element.select_option(label=text)
            return True
    for text in labels:
        if text.lower().startswith(desired):
            await select_element.select_option(label=text)
            return True
    return False


async def harvest_user_filled_fields(page, contact: Dict, recurring_answers: Optional[Dict], session: Session) -> int:
    """
    Reads fields the agent left blank and the user has since filled.
    Anything already explained by contact details or recurring answers
    is left alone. New answers are saved for the next application.
    """
    learned = load_learned_map(session)
    saved = await harvest_radio_groups(page, contact, recurring_answers, learned, session)
    controls = page.locator(
        "input[type='text'], input[type='email'], input[type='tel'], input:not([type]), textarea, select"
    )
    count = await controls.count()
    for i in range(count):
        element = controls.nth(i)
        try:
            if not await element.is_visible():
                continue
            input_type = (await element.get_attribute("type") or "").lower()
            if input_type in ("password", "file", "hidden", "checkbox", "radio"):
                continue
            value = await _read_control_value(element)
            if not value:
                continue
            field_text = await get_field_identifier(page, element)
            if not field_text or is_protected_field(field_text):
                continue
            known = desired_field_value(field_text, contact, recurring_answers, learned)
            if known:
                continue
            if remember_answer(session, field_text, value):
                saved += 1
                learned[question_key(field_text)] = value
                print(f"Learned answer for: {question_label(field_text)[:60]}")
        except Exception:
            continue
    if saved:
        session.commit()
    return saved


async def handle_resume_selection(page):
    """
    Handles the specific Indeed flow where a resume is already selected.
    In the API version, we automatically check if 'upload' is needed
    based on user preferences or simply continue.
    """
    try:
        await page.wait_for_timeout(3000)

        continue_options = [
            page.get_by_role("button", name="Continue", exact=True),
            page.locator("button:has-text('Continue')"),
            page.locator("a:has-text('Continue')"),
            page.locator("span[role='button']:has-text('Continue')"),
            page.get_by_text("Continue", exact=True)
        ]

        found_continue = False
        for opt in continue_options:
            if await opt.first.is_visible():
                found_continue = True
                break

        if found_continue:
            # Default to using existing CV for automation; can be overridden in API logic
            print("  Resume detected. Using existing CV.")
            return True

        keywords = ["resume options", "change resume", "upload a different"]
        buttons = page.locator("button, a, span[role='button']")
        clicked_options = False
        for i in range(await buttons.count()):
            btn = buttons.nth(i)
            text = (await btn.inner_text()).lower()
            if any(k in text for k in keywords) and await btn.is_visible():
                await btn.click()
                print(f"  Clicked resume options button: '{text.strip()}'")
                clicked_options = True
                break

        if clicked_options:
            await page.wait_for_timeout(2000)
            upload_keywords = ["upload", "different file", "upload a different"]
            menu_buttons = page.locator("button, a, span[role='button']")
            for i in range(await menu_buttons.count()):
                btn = menu_buttons.nth(i)
                text = (await btn.inner_text()).lower()
                if any(k in text for k in upload_keywords) and await btn.is_visible():
                    await btn.click()
                    print(f"  Clicked final upload button: '{text.strip()}'")
                    await page.wait_for_timeout(1000)
                    return True
    except Exception as e:
        print(f"  Error in resume selection: {e}")
    return False


async def _radio_groups(page) -> Dict[str, list]:
    groups: Dict[str, list] = {}
    radios = page.locator("input[type='radio']")
    count = await radios.count()
    for i in range(count):
        radio = radios.nth(i)
        try:
            if not await radio.is_visible():
                continue
            name = await radio.get_attribute("name") or f"radio-{i}"
            groups.setdefault(name, []).append(radio)
        except Exception:
            continue
    return groups


async def _radio_question(page, radio) -> str:
    legend = radio.locator("xpath=ancestor::fieldset[1]/legend")
    try:
        if await legend.count() > 0:
            text = " ".join((await legend.first.inner_text()).split())
            if text:
                return text
    except Exception:
        pass
    labelled = await radio.get_attribute("aria-labelledby")
    if labelled:
        try:
            label = page.locator(f"#{labelled.split()[0]}")
            if await label.count() > 0:
                return " ".join((await label.first.inner_text()).split())
        except Exception:
            pass
    return await get_field_identifier(page, radio)


async def _radio_option_label(page, radio) -> str:
    id_attr = await radio.get_attribute("id")
    if id_attr:
        try:
            label = page.locator(f"label[for='{id_attr}']")
            if await label.count() > 0:
                return " ".join((await label.first.inner_text()).split())
        except Exception:
            pass
    try:
        parent = radio.locator("xpath=..")
        if await parent.count() > 0:
            return " ".join((await parent.first.inner_text()).split())
    except Exception:
        pass
    return (await radio.get_attribute("value") or "").strip()


async def fill_radio_groups(page, contact, recurring_answers, learned) -> None:
    """Selects a saved Yes/No (or other choice) when this question was answered before."""
    for radios in (await _radio_groups(page)).values():
        try:
            question = await _radio_question(page, radios[0])
            desired = desired_field_value(question, contact, recurring_answers, learned)
            if not desired:
                continue
            wanted = desired.strip().lower()
            for radio in radios:
                label = (await _radio_option_label(page, radio)).lower()
                if label == wanted:
                    await radio.check()
                    print(f"Reused saved choice: {question[:60]} -> {desired}")
                    break
        except Exception:
            continue


async def harvest_radio_groups(page, contact, recurring_answers, learned, session: Session) -> int:
    """Saves a choice the user selected when the agent had no answer for that question."""
    saved = 0
    for radios in (await _radio_groups(page)).values():
        try:
            chosen = None
            for radio in radios:
                if await radio.is_checked():
                    chosen = radio
                    break
            if chosen is None:
                continue
            question = await _radio_question(page, chosen)
            answer = await _radio_option_label(page, chosen)
            if not question or not answer or is_protected_field(question):
                continue
            known = desired_field_value(question, contact, recurring_answers, learned)
            if known:
                continue
            if remember_answer(session, question, answer):
                saved += 1
                learned[question_key(question)] = answer
                print(f"Learned choice for: {question_label(question)[:60]}")
        except Exception:
            continue
    return saved


async def fill_known_fields(page, contact, recurring_answers=None, session: Optional[Session] = None, cv_path: Optional[str] = None, cv_name: Optional[str] = None):
    """
    Scans and fills known contact and logistics fields.
    `cv_path` is the candidate's uploaded CV (from their Profile) — passed in
    explicitly so this function doesn't depend on a hardcoded path.
    """
    if await handle_resume_selection(page):
        await page.wait_for_timeout(2000)

    try:
        await page.evaluate("() => window.scrollTo(0, 0)")
    except Exception:
        pass

    filled = []
    skipped = []
    learned = load_learned_map(session)
    await fill_radio_groups(page, contact, recurring_answers, learned)

    password_fields = page.locator("input[type='password']")
    if await password_fields.count() > 0:
        print("\n⚠ This application requires creating an account (password field detected).")
        print("  The process will stop here for manual account creation.")

    input_types = ["input[type='text']", "input[type='email']", "input[type='tel']", "input[type='file']", "input:not([type])"]
    for selector in input_types:
        inputs = page.locator(selector)
        count = await inputs.count()
        for i in range(count):
            input_element = inputs.nth(i)
            try:
                if not await input_element.is_visible():
                    continue
                aria_autocomplete = await input_element.get_attribute("aria-autocomplete")
                input_id = await input_element.get_attribute("id") or ""
                if aria_autocomplete or "select" in input_id.lower():
                    field_text = await get_field_identifier(page, input_element)
                    if is_protected_field(field_text):
                        skipped.append(f"[dropdown-widget] {field_text.strip()[:40]}" if field_text else "[dropdown-widget] (unidentified)")
                    else:
                        desired_answer = None
                        if ("which country" in field_text or "country in which" in field_text or field_text.strip().startswith("country")) and contact.get("country"):
                            desired_answer = contact["country"]
                        else:
                            desired_answer = desired_field_value(field_text, contact, recurring_answers, learned)
                        if desired_answer:
                            was_selected = await select_dropdown_option(page, input_element, desired_answer)
                            if was_selected:
                                filled.append(f"[dropdown] {field_text.strip()[:40]} -> {desired_answer}")
                            else:
                                skipped.append(f"[dropdown-no-match] {field_text.strip()[:40]}")
                        else:
                            skipped.append(f"[dropdown-widget] {field_text.strip()[:40]}" if field_text else "[dropdown-widget] (unidentified)")
                    continue

                field_text = await get_field_identifier(page, input_element)
                if not field_text:
                    skipped.append("(unidentified field)")
                    continue
                value = match_field_to_value(field_text, contact)
                if value == "__UPLOAD_CV__":
                    if not cv_path:
                        skipped.append(f"{field_text.strip()[:40]} -> [no CV uploaded in Profile]")
                        continue
                    try:
                        await input_element.set_input_files(upload_file(cv_path, cv_name))
                        filled.append(f"{field_text.strip()[:40]} -> [CV Uploaded]")
                    except Exception as e:
                        skipped.append(f"CV upload failed: {e}")
                    continue
                if not value:
                    value = desired_field_value(field_text, contact, recurring_answers, learned)
                if value:
                    await input_element.fill(value)
                    filled.append(f"{field_text.strip()[:40]} -> {value}")
                else:
                    skipped.append(field_text.strip()[:40])
            except Exception as e:
                skipped.append(f"(error reading field: {e})")

    select_elements = page.locator("select")
    select_count = await select_elements.count()
    for i in range(select_count):
        select_element = select_elements.nth(i)
        try:
            if not await select_element.is_visible():
                continue
            field_text = await get_field_identifier(page, select_element)
            desired_answer = desired_field_value(field_text, contact, recurring_answers, learned) if field_text else None
            if desired_answer and await select_native_option(select_element, desired_answer):
                filled.append(f"[dropdown] {field_text.strip()[:40]} -> {desired_answer}")
            else:
                skipped.append(f"[dropdown] {field_text.strip()[:40]}" if field_text else "[dropdown] (unidentified)")
        except Exception:
            continue

    return {"filled": filled, "skipped": skipped}


def _is_filename(label: str) -> bool:
    return bool(re.search(r"\.(pdf|docx?|rtf)\b", label or "", re.I))


async def _apply_text_answers(page, answered_items, applied: List[str]) -> None:
    inputs = page.locator("input[type='text'], input[type='email'], input[type='tel'], input:not([type])")
    count = await inputs.count()
    for i in range(count):
        element = inputs.nth(i)
        try:
            if not await element.is_visible():
                continue
            input_type = (await element.get_attribute("type") or "").lower()
            if input_type in ("password", "file", "hidden", "checkbox", "radio", "submit", "button"):
                continue
            field_text = await get_field_identifier(page, element)
            if not field_text:
                continue
            for question_text, final_answer in answered_items:
                if final_answer and questions_match(field_text, question_text):
                    await element.fill(final_answer)
                    applied.append(question_text)
                    break
        except Exception:
            continue


async def _apply_radio_answers(page, answered_items, applied: List[str]) -> None:
    for radios in (await _radio_groups(page)).values():
        try:
            question = await _radio_question(page, radios[0])
            labels = []
            for radio in radios:
                labels.append((radio, await _radio_option_label(page, radio)))
            filenames = [label for _, label in labels if label]
            resume_choice = None
            if filenames and all(_is_filename(label) for label in filenames):
                for question_text, final_answer in answered_items:
                    if final_answer and "resume" in question_text.lower() and _is_filename(final_answer):
                        resume_choice = final_answer
                        break
            wanted = resume_choice
            if wanted is None:
                for question_text, final_answer in answered_items:
                    if final_answer and questions_match(question, question_text):
                        wanted = final_answer
                        break
            if not wanted:
                continue
            for radio, label in labels:
                if label.lower() == wanted.strip().lower():
                    await radio.check()
                    applied.append(question)
                    break
        except Exception:
            continue


async def _apply_select_answers(page, answered_items, applied: List[str]) -> None:
    selects = page.locator("select")
    count = await selects.count()
    for i in range(count):
        element = selects.nth(i)
        try:
            if not await element.is_visible():
                continue
            field_text = await get_field_identifier(page, element)
            if not field_text:
                continue
            for question_text, final_answer in answered_items:
                if final_answer and questions_match(field_text, question_text):
                    if await select_native_option(element, final_answer):
                        applied.append(question_text)
                    break
        except Exception:
            continue


async def _apply_combobox_answers(page, answered_items, applied: List[str]) -> None:
    combos = page.locator("[role='combobox']")
    count = await combos.count()
    for i in range(count):
        element = combos.nth(i)
        try:
            if not await element.is_visible():
                continue
            if (await element.input_value()).strip():
                continue
            field_text = await get_field_identifier(page, element)
            if not field_text:
                continue
            for question_text, final_answer in answered_items:
                if final_answer and questions_match(field_text, question_text):
                    if await select_dropdown_option(page, element, final_answer):
                        applied.append(question_text)
                    break
        except Exception:
            continue


async def _apply_checkbox_answers(page, answered_items, applied: List[str]) -> None:
    boxes = page.locator("input[type='checkbox']")
    count = await boxes.count()
    groups: Dict[str, list] = {}
    for i in range(count):
        element = boxes.nth(i)
        try:
            if not await element.is_visible():
                continue
            name = await element.get_attribute("name") or await element.get_attribute("id") or str(i)
            groups.setdefault(name, []).append(element)
        except Exception:
            continue
    for group in groups.values():
        try:
            legend = group[0].locator("xpath=ancestor::fieldset[1]/legend")
            if await legend.count():
                question = " ".join((await legend.first.inner_text()).split())
            else:
                question = await get_field_identifier(page, group[0])
            wanted = None
            for question_text, final_answer in answered_items:
                if final_answer and questions_match(question, question_text):
                    wanted = final_answer
                    break
            if not wanted:
                continue
            chosen = {part.strip().lower() for part in re.split(r"[\n,]", wanted) if part.strip()}
            for box in group:
                box_id = await box.get_attribute("id")
                label = ""
                if box_id:
                    lab = page.locator(f"label[for='{box_id}']")
                    if await lab.count():
                        label = " ".join((await lab.first.inner_text()).split())
                if label.lower() in chosen:
                    await box.check()
            applied.append(question)
        except Exception:
            continue


async def type_confirmed_answers(page, job_id: str, session: Session) -> None:
    """Types answers the user already confirmed, including accepted drafts."""
    rows = session.exec(select(ApplicationAnswer).where(ApplicationAnswer.job_id == job_id)).all()
    items = []
    for row in rows:
        text = (row.final_answer or row.draft_answer or "").strip()
        if text:
            items.append((row.question, text))
    if items:
        await apply_final_answers_to_page(page, items)


_BLOCKER_SCRIPT = """
() => {
  const clean = (value) => (value || "").replace(/\\s+/g, " ").trim();
  const visible = (el) => {
    const style = window.getComputedStyle(el);
    if (style.display === "none" || style.visibility === "hidden") return false;
    const rect = el.getBoundingClientRect();
    return rect.width > 0 && rect.height > 0;
  };
  const dialogs = [...document.querySelectorAll("dialog[open], [role='dialog']")].filter((node) => {
    return visible(node) && (node.innerText || "").trim().length > 0;
  });
  const root = dialogs.length ? dialogs[dialogs.length - 1] : document.body;
  const fileName = (value) => /\\.(pdf|docx?|rtf)\\b/i.test(value || "");
  const placeholder = (value) => !value || /^select(?:\\s+an option|\\.{3})?$/i.test(clean(value));

  function fieldCount(node) {
    const inputs = node.querySelectorAll("textarea, select, input:not([type='hidden']):not([type='radio'])");
    const radios = new Set([...node.querySelectorAll("input[type='radio']")].map((radio) => radio.name || radio.id || "radio"));
    return inputs.length + radios.size;
  }

  function looksRequired(el) {
    if (!el) return false;
    if (el.required || el.getAttribute("aria-required") === "true") return true;
    let node = el;
    for (let i = 0; i < 6 && node && node !== root.parentElement; i++) {
      const text = clean(node.innerText || "");
      if (text.length <= 420 && fieldCount(node) <= 2) {
        if (/this field is required/i.test(text)) return true;
        if (node.querySelector("[class*='required']")) return true;
      }
      node = node.parentElement;
    }
    return false;
  }

  function questionFrom(el) {
    const id = el.getAttribute("id");
    if (id) {
      const label = root.querySelector(`label[for="${CSS.escape(id)}"]`);
      if (label) {
        const text = clean(label.innerText).replace(/\\*+$/, "").trim();
        if (text) return text;
      }
    }
    const labelled = el.getAttribute("aria-labelledby");
    if (labelled) {
      const node = document.getElementById(labelled.split(/\\s+/)[0]);
      if (node) {
        const text = clean(node.innerText).replace(/\\*+$/, "").trim();
        if (text) return text;
      }
    }
    const legend = el.closest("fieldset") && el.closest("fieldset").querySelector("legend");
    if (legend) {
      const text = clean(legend.innerText).replace(/\\*+$/, "").trim();
      if (text) return text;
    }
    let node = el.parentElement;
    for (let i = 0; i < 6 && node && node !== root; i++) {
      if (clean(node.innerText).length <= 420 && fieldCount(node) <= 2) {
        const copy = node.cloneNode(true);
        copy.querySelectorAll("input, select, textarea, button, option").forEach((child) => child.remove());
        const text = clean(copy.innerText).replace(/this field is required/ig, "").replace(/\\*+$/, "").trim();
        if (text) return text;
      }
      node = node.parentElement;
    }
    return "";
  }

  function legendQuestion(el) {
    const fieldset = el.closest("fieldset");
    if (fieldset) {
      const legend = fieldset.querySelector("legend");
      if (legend) {
        const text = clean(legend.innerText).replace(/\\*+$/, "").replace(/:+$/, "").trim();
        if (text) return text;
      }
    }
    return questionFrom(el);
  }

  const found = [];
  const seen = new Set();
  const add = (question, kind, choices, draft) => {
    const label = clean(question).replace(/\\*+$/, "").replace(/:+$/, "").trim();
    if (!label || label.length < 3 || seen.has(label.toLowerCase())) return;
    seen.add(label.toLowerCase());
    found.push({ question: label, kind, choices: choices || [], draft: draft || "" });
  };

  root.querySelectorAll("select").forEach((el) => {
    if (!visible(el)) return;
    const selected = el.options[el.selectedIndex];
    const value = clean(selected ? selected.text : "");
    const current = placeholder(value) ? "" : value;
    if (!looksRequired(el) && !current) return;
    const choices = [...el.options].map((option) => clean(option.text)).filter((text) => text && !placeholder(text));
    add(questionFrom(el), "select", choices, current);
  });

  const groups = new Map();
  root.querySelectorAll("input[type='radio']").forEach((el) => {
    if (!visible(el)) return;
    const name = el.getAttribute("name") || "";
    if (!groups.has(name)) groups.set(name, []);
    groups.get(name).push(el);
  });
  groups.forEach((radios) => {
    const labels = radios.map((radio) => {
      const id = radio.getAttribute("id");
      const text = id ? (root.querySelector(`label[for="${CSS.escape(id)}"]`) || {}).innerText : "";
      return clean(text || (radio.parentElement ? radio.parentElement.innerText : radio.value));
    }).filter(Boolean);
    if (labels.length && labels.every(fileName)) return;
    const checked = radios.find((radio) => radio.checked);
    let current = "";
    if (checked) {
      const id = checked.getAttribute("id");
      const label = id && root.querySelector(`label[for="${CSS.escape(id)}"]`);
      current = clean(label ? label.innerText : checked.value);
    }
    if (!radios.some(looksRequired) && !current) return;
    add(legendQuestion(radios[0]), "radio", labels, current);
  });

  const checks = new Map();
  root.querySelectorAll("input[type='checkbox']").forEach((el) => {
    if (!visible(el)) return;
    const name = el.getAttribute("name") || el.id || "checkbox";
    if (!checks.has(name)) checks.set(name, []);
    checks.get(name).push(el);
  });
  checks.forEach((boxes) => {
    if (!boxes.some(looksRequired) && !boxes.some((box) => box.checked)) return;
    const choices = [];
    const selected = [];
    boxes.forEach((box) => {
      const id = box.getAttribute("id");
      const label = id && root.querySelector(`label[for="${CSS.escape(id)}"]`);
      const text = clean(label ? label.innerText : "");
      if (!text) return;
      choices.push(text);
      if (box.checked) selected.push(text);
    });
    add(legendQuestion(boxes[0]), "checkbox", choices, selected.join("\\n"));
  });

  root.querySelectorAll("[role='combobox']").forEach((el) => {
    if (!visible(el)) return;
    const control = el.closest(".select__control") || el.parentElement;
    const shown = control && control.querySelector(".select__single-value, [class*='single-value']");
    const value = clean(shown ? shown.innerText : el.value);
    const current = placeholder(value) ? "" : value;
    if (!looksRequired(el) && !current) return;
    add(questionFrom(el), "select", [], current);
  });

  root.querySelectorAll("textarea, input[type='text'], input:not([type])").forEach((el) => {
    if (!visible(el) || !looksRequired(el)) return;
    if (el.getAttribute("role") === "combobox") return;
    const type = (el.getAttribute("type") || "").toLowerCase();
    if (["password", "file", "hidden", "checkbox", "radio", "submit", "button"].includes(type)) return;
    if (clean(el.value)) return;
    add(questionFrom(el), "text", [], "");
  });

  return found;
}
"""


async def _short_question(page, element) -> str:
    """The label a person sees, without the field id mixed in."""
    element_id = await element.get_attribute("id")
    if element_id:
        label = page.locator(f"label[for='{element_id}']")
        try:
            if await label.count():
                return " ".join((await label.first.inner_text()).split()).rstrip("*").strip(" :")
        except Exception:
            pass
    labelled = await element.get_attribute("aria-labelledby")
    if labelled:
        node = page.locator(f"#{labelled.split()[0]}")
        try:
            if await node.count():
                return " ".join((await node.first.inner_text()).split()).rstrip("*").strip(" :")
        except Exception:
            pass
    return question_label(await get_field_identifier(page, element))


async def _combo_value(element) -> str:
    try:
        value = await element.evaluate(
            """el => {
                const control = el.closest('.select__control') || el.parentElement;
                const shown = control && control.querySelector(".select__single-value, [class*='single-value']");
                return ((shown && shown.innerText) || el.value || '').replace(/\\s+/g, ' ').trim();
            }"""
        )
    except Exception:
        return ""
    if not value or re.match(r"^select(\.\.\.| an option)?$", value, re.I):
        return ""
    return value


def _is_dial_code_list(choices: List[str]) -> bool:
    """Phone-country menus look like 'Nigeria+234'. They are not the options for other questions."""
    if len(choices) < 8:
        return False
    coded = sum(1 for choice in choices if re.search(r"\+\d+\s*$", choice))
    return coded >= max(6, int(len(choices) * 0.6))


async def _open_and_read_options(page, element) -> List[str]:
    """Opens one dropdown and reads only that menu, then closes it without choosing."""
    owner = page if hasattr(page, "keyboard") else page.page
    try:
        await element.click(timeout=2000)
        await page.wait_for_timeout(250)
    except Exception:
        return []
    collected: List[str] = []
    seen = set()
    try:
        controls = await element.get_attribute("aria-controls")
        if not controls:
            return []
        listbox = page.locator(f"[id='{controls}']")
        if not await listbox.count():
            return []
        menu = listbox.first
        for _ in range(6):
            options = menu.locator("[role='option']")
            count = await options.count()
            added = False
            for index in range(min(count, 80)):
                option = options.nth(index)
                try:
                    if not await option.is_visible():
                        continue
                    text = " ".join((await option.inner_text()).split())
                except Exception:
                    continue
                key = text.lower()
                if not text or key in seen or re.match(r"^select(\.\.\.| an option)?$", text, re.I):
                    continue
                seen.add(key)
                collected.append(text)
                added = True
            try:
                moved = await menu.evaluate(
                    "el => { const before = el.scrollTop; el.scrollTop += el.clientHeight; return el.scrollTop !== before; }"
                )
            except Exception:
                break
            if not added or not moved:
                break
            await page.wait_for_timeout(60)
    finally:
        try:
            await owner.keyboard.press("Escape")
        except Exception:
            pass
    return collected


async def _attach_dropdown_options(page, blockers: List[Dict]) -> None:
    """Greenhouse keeps the choice list closed until the dropdown is opened."""
    combos = page.locator("[role='combobox']")
    try:
        count = await combos.count()
    except Exception:
        return
    for index in range(count):
        element = combos.nth(index)
        try:
            if not await element.is_visible():
                continue
            question = await _short_question(page, element)
            if not question:
                continue
            current = await _combo_value(element)
            choices = await _open_and_read_options(page, element)
            if _is_dial_code_list(choices) and not re.search(r"\b(country|phone|dial)\b", question, re.I):
                choices = []
            match = next((item for item in blockers if question_key(item["question"]) == question_key(question)), None)
            if match is None:
                if not current and not choices:
                    continue
                blockers.append({"question": question, "kind": "select", "choices": choices, "draft": current})
                continue
            match["choices"] = choices
            if current and not match.get("draft"):
                match["draft"] = current
            match["kind"] = "select"
        except Exception:
            continue


async def unanswered_required(page) -> List[Dict]:
    """
    Required fields still empty, plus dropdowns and multi-selects so the
    person can see what was filled and pick a different option.
    """
    try:
        blockers = await page.evaluate(_BLOCKER_SCRIPT)
    except Exception as e:
        print(f"Could not read required fields: {e}")
        blockers = []
    cleaned = []
    for blocker in blockers or []:
        question = (blocker.get("question") or "").strip()
        if not question:
            continue
        choices = [choice.strip() for choice in blocker.get("choices") or [] if choice and choice.strip()]
        cleaned.append({
            "question": question,
            "kind": blocker.get("kind") or "text",
            "choices": choices,
            "draft": (blocker.get("draft") or "").strip(),
        })
    await _attach_dropdown_options(page, cleaned)
    return cleaned


def _is_reviewed(session: Session, job_id: str, question: str) -> bool:
    row = _find_application_answer(session, job_id, question)
    return bool(row and row.is_reviewed)


def store_blockers(session: Session, job_id: str, blockers: List[Dict]) -> None:
    kept = []
    for blocker in blockers:
        row = upsert_application_question(
            session,
            job_id,
            blocker["question"],
            draft=blocker.get("draft") or None,
            choices=blocker.get("choices"),
            kind=blocker.get("kind"),
        )
        kept.append(row.answer_id)
    stale = session.exec(select(ApplicationAnswer).where(ApplicationAnswer.job_id == job_id)).all()
    for row in stale:
        if row.is_reviewed or row.answer_id in kept:
            continue
        session.delete(row)
    session.commit()


async def _dialog_scope(page):
    """A visible dialog only. Greenhouse keeps an empty hidden dialog in the form."""
    dialog = page.locator("dialog[open], [role='dialog']")
    try:
        count = await dialog.count()
    except Exception:
        return page
    for index in range(count - 1, -1, -1):
        item = dialog.nth(index)
        try:
            if await item.is_visible():
                return item
        except Exception:
            continue
    return page


async def page_asks_for_cover_letter(page) -> bool:
    """True when this step has a cover-letter upload, even if the heading is inside the form frame."""
    text = await _page_text(page)
    if "cover letter" in text:
        return True
    files = page.locator("input[type='file']")
    try:
        count = await files.count()
    except Exception:
        return False
    for index in range(count):
        element = files.nth(index)
        try:
            token = " ".join([
                await element.get_attribute("id") or "",
                await element.get_attribute("name") or "",
            ]).lower()
        except Exception:
            continue
        if "cover" in token:
            return True
    return False


async def _page_text(page) -> str:
    try:
        scope = await _dialog_scope(page)
        return " ".join((await scope.inner_text()).split()).lower()
    except Exception:
        return ""


COVER_LETTER_QUESTION = "Cover letter"
COVER_LETTER_FILENAME = "Cover Letter.pdf"


def _safe_upload_name(display_name: str, fallback: str) -> str:
    """The name the employer sees. Stored files keep their own names on disk."""
    from pathlib import Path

    name = Path(display_name or "").name
    name = re.sub(r"[^\w.\- ()]+", " ", name)
    name = " ".join(name.split())
    if not name or name in {".", ".."}:
        name = Path(fallback).name
    return name


def upload_file(path: str, display_name: Optional[str] = None):
    """A Playwright file payload that keeps the person's filename on the form."""
    from pathlib import Path

    source = Path(path)
    name = _safe_upload_name(display_name or source.name, source.name)
    if source.suffix and not name.lower().endswith(source.suffix.lower()):
        name = f"{name}{source.suffix}"
    mime = "application/pdf" if name.lower().endswith(".pdf") else "application/octet-stream"
    return {"name": name, "mimeType": mime, "buffer": source.read_bytes()}


def cover_letter_path(job_id: str):
    from pathlib import Path
    from src.api.config import settings

    folder = Path(settings.uploads_dir).parent / "cover_letters"
    folder.mkdir(parents=True, exist_ok=True)
    return folder / f"{job_id}.pdf"


def write_text_pdf(path, text: str) -> None:
    """A small text PDF, so a cover letter can be uploaded without extra libraries."""
    safe = (text or "").encode("latin-1", "replace").decode("latin-1")
    lines = []
    for paragraph in safe.replace("\r", "").split("\n"):
        words = paragraph.split()
        if not words:
            lines.append("")
            continue
        current = ""
        for word in words:
            trial = word if not current else f"{current} {word}"
            if len(trial) > 90 and current:
                lines.append(current)
                current = word
            else:
                current = trial
        if current:
            lines.append(current)
    if not lines:
        lines = [""]

    pages = [lines[index:index + 42] for index in range(0, len(lines), 42)]

    def escape(value: str) -> str:
        return value.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")

    contents = []
    for page_lines in pages:
        commands = ["BT", "/F1 11 Tf", "72 740 Td", "14 TL"]
        for index, line in enumerate(page_lines):
            if index:
                commands.append("T*")
            commands.append(f"({escape(line)}) Tj")
        commands.append("ET")
        contents.append("\n".join(commands).encode("latin-1"))

    page_count = len(contents)
    content_ids = list(range(4, 4 + page_count))
    page_ids = list(range(4 + page_count, 4 + page_count * 2))
    objects = {
        1: b"<< /Type /Catalog /Pages 2 0 R >>",
        2: (
            f"<< /Type /Pages /Count {page_count} /Kids [{' '.join(f'{pid} 0 R' for pid in page_ids)}] >>"
        ).encode("latin-1"),
        3: b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
    }
    for index, body in enumerate(contents):
        objects[content_ids[index]] = b"<< /Length %d >>\nstream\n" % len(body) + body + b"\nendstream"
        objects[page_ids[index]] = (
            f"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents {content_ids[index]} 0 R "
            f"/Resources << /Font << /F1 3 0 R >> >> >>"
        ).encode("latin-1")

    output = bytearray(b"%PDF-1.4\n")
    offsets = {}
    total = 3 + page_count * 2
    for number in range(1, total + 1):
        offsets[number] = len(output)
        output += f"{number} 0 obj\n".encode("latin-1")
        output += objects[number]
        output += b"\nendobj\n"
    xref = len(output)
    output += f"xref\n0 {total + 1}\n".encode("latin-1")
    output += b"0000000000 65535 f \n"
    for number in range(1, total + 1):
        output += f"{offsets[number]:010d} 00000 n \n".encode("latin-1")
    output += (
        f"trailer << /Size {total + 1} /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF"
    ).encode("latin-1")
    path.write_bytes(bytes(output))


def _cv_for_letter(cv_text: str) -> str:
    """The CV with contact lines removed, so the letter is not a copy of the header."""
    kept = []
    for line in (cv_text or "").splitlines():
        if re.search(r"@|\+\d{6,}|linkedin\.com|https?://", line, re.I):
            continue
        kept.append(line)
    return "\n".join(kept)[:6000]


def _letter_is_dump(text: str) -> bool:
    """A pasted CV header is not a letter."""
    if not text:
        return True
    if "@" in text or "|" in text:
        return True
    if re.search(r"\+\d{8,}", text):
        return True
    lowered = text.lower()
    if "summary" in lowered and "linkedin" in lowered:
        return True
    return False


def draft_cover_letter(job, cv_text: str) -> str:
    """A plain letter. Only facts from the CV, and only where they meet this job."""
    from src.Agent.ai_generator import generate_answer
    from src.Agent.parse_cv import build_candidate_summary

    cv = _cv_for_letter(cv_text)
    description = " ".join((getattr(job, "description", "") or "").split())[:4000]
    title = getattr(job, "title", "") or "this role"
    company = getattr(job, "company", "") or "the company"
    prompt = f"""Write a cover letter for the {title} role at {company}.

Use only facts that appear in the CV below, and only the ones that relate to the job description. Do not invent employers, dates, tools, or results. Do not include an email, phone number, or link. Do not copy the CV as a list or a header.

Write the way a person would, in 3 short paragraphs, first person. No greeting and no sign-off. Do not use the words leverage, passionate, thrilled, delve, cutting-edge, synergy, utilize, robust, dynamic, or excited.

Job description:
{description}

CV:
{cv}

Letter:"""
    drafted = generate_answer(prompt, max_tokens=500)
    if drafted and not _letter_is_dump(drafted):
        return drafted.strip()
    summary = " ".join(build_candidate_summary(cv_text).split())
    summary = re.sub(r"@|\+\d{6,}|https?://\S+|linkedin\.com\S*", "", summary, flags=re.I)
    summary = " ".join(summary.split())[:900]
    if summary:
        return f"I am applying for the {title} role at {company}. {summary}".strip()
    return f"I am applying for the {title} role at {company}."


def stage_cover_letter(session: Session, job, cv_text: str):
    """
    Drafts the letter and holds it for review.

    Returns (upload_path, blocker). The file is written only after the person
    has seen the draft. Until then the blocker opens the review window.
    """
    row = _find_application_answer(session, job.job_id, COVER_LETTER_QUESTION)
    saved = (row.final_answer or "").strip() if row else ""
    if row and row.is_reviewed and saved and not _letter_is_dump(saved):
        path = cover_letter_path(job.job_id)
        write_text_pdf(path, saved)
        return str(path), None
    if row and _letter_is_dump(saved or row.draft_answer or ""):
        row.is_reviewed = False
        row.final_answer = None
        row.draft_answer = ""
        session.add(row)

    draft = (row.draft_answer or "").strip() if row else ""
    if not draft or _letter_is_dump(draft):
        draft = draft_cover_letter(job, cv_text)
        if row:
            row.draft_answer = draft
            row.final_answer = None
            session.add(row)
            session.commit()
        else:
            upsert_application_question(session, job.job_id, COVER_LETTER_QUESTION, draft=draft)
            session.commit()
        print("Drafted a cover letter for review.")
    return None, {"question": COVER_LETTER_QUESTION, "kind": "text", "choices": [], "draft": draft}


async def prepare_application_documents(
    page,
    cv_path: Optional[str],
    cover_path: Optional[str],
    cv_name: Optional[str] = None,
) -> None:
    """Uploads the profile CV and the drafted cover letter when this step asks for them."""
    scope = await _dialog_scope(page)
    inputs = scope.locator("input[type='file']")
    count = await inputs.count()
    attached_resume = False
    attached_cover = False
    for i in range(count):
        element = inputs.nth(i)
        try:
            field_id = (await element.get_attribute("id") or "").lower()
            field_name = (await element.get_attribute("name") or "").lower()
            purpose = await get_field_identifier(page, element)
            try:
                parent = element.locator("xpath=..")
                if await parent.count():
                    purpose = f"{purpose} {' '.join((await parent.first.inner_text()).split())}"
            except Exception:
                pass
            purpose = purpose.lower()
            is_cover = "cover" in field_id or "cover" in field_name or ("cover" in purpose and "resume" not in field_id)
            is_resume = not is_cover and (
                "resume" in field_id or field_id == "cv" or "resume" in field_name or field_name == "cv"
                or "resume" in purpose or bool(re.search(r"\bcv\b", purpose))
            )
            if is_cover and cover_path:
                await element.set_input_files(upload_file(cover_path, COVER_LETTER_FILENAME))
                attached_cover = True
                print("Uploaded cover letter.")
            elif is_resume and cv_path:
                await element.set_input_files(upload_file(cv_path, cv_name))
                attached_resume = True
                print(f"Uploaded resume as {cv_name or 'the profile CV'}.")
        except Exception as e:
            print(f"Could not attach a file: {e}")

    page_text = await _page_text(page)
    if cover_path and not attached_cover and "cover letter" in page_text:
        await _choose_file(page, r"upload cover letter", cover_path, COVER_LETTER_FILENAME)
    if cv_path and not attached_resume and re.search(r"\bresume\b|\bcv\b", page_text):
        if count == 1:
            try:
                await inputs.first.set_input_files(upload_file(cv_path, cv_name))
                print(f"Uploaded resume as {cv_name or 'the profile CV'}.")
                return
            except Exception:
                pass
        await _choose_file(page, r"upload resume|resume/cv|attach", cv_path, cv_name)


_ATS_HOSTS = ("greenhouse.io", "lever.co", "ashbyhq.com", "myworkdayjobs.com", "smartrecruiters.com")


async def application_scope(page):
    """
    The document that actually holds the application. Company sites such as
    Nextiva embed Greenhouse or Lever in an iframe, which the main page
    locators never see.
    """
    frames = getattr(page, "frames", None)
    if not frames:
        return page

    best = None
    best_count = 0
    for frame in frames:
        if frame == page.main_frame:
            continue
        url = (frame.url or "").lower()
        try:
            count = await frame.locator(
                "input[type='text'], input[type='email'], input[type='tel'], input:not([type]), textarea, select"
            ).count()
        except Exception:
            count = 0
        if any(host in url for host in _ATS_HOSTS) and count:
            return frame
        if count > best_count:
            best = frame
            best_count = count
    if best is not None and best_count >= 3:
        return best
    return page


async def focus_application(page, scope) -> None:
    """Brings the embedded form into view without scrolling the page past it."""
    if scope is page:
        return
    try:
        element = await scope.frame_element()
        await element.scroll_into_view_if_needed(timeout=3000)
    except Exception:
        pass


async def dismiss_overlays(page) -> None:
    """Closes a cookie notice that sits on top of the application form."""
    names = (
        r"^Accept All Cookies$",
        r"^Accept all cookies$",
        r"^Accept all$",
        r"^Allow all cookies$",
        r"^Allow all$",
        r"^I agree$",
    )
    for pattern in names:
        button = page.get_by_role("button", name=re.compile(pattern, re.I))
        try:
            if await button.count() and await button.first.is_visible():
                await button.first.click(timeout=3000)
                await page.wait_for_timeout(400)
                print("Closed the cookie notice.")
                return
        except Exception:
            continue
    try:
        fallback = page.locator("#onetrust-accept-btn-handler")
        if await fallback.count() and await fallback.first.is_visible():
            await fallback.first.click(timeout=3000)
            print("Closed the cookie notice.")
    except Exception:
        pass


async def _choose_file(page, button_name: str, path: str, display_name: Optional[str] = None) -> None:
    scope = await _dialog_scope(page)
    button = scope.get_by_role("button", name=re.compile(button_name, re.I))
    if not await button.count():
        button = scope.get_by_text(re.compile(button_name, re.I))
    try:
        if not await button.count() or not await button.first.is_visible():
            return
        owner = page if hasattr(page, "expect_file_chooser") else page.page
        async with owner.expect_file_chooser(timeout=3000) as chooser_info:
            await button.first.click()
        await (await chooser_info.value).set_files(upload_file(path, display_name))
        print(f"Uploaded file via {button_name}.")
    except Exception as e:
        print(f"Could not open the file picker for {button_name}: {e}")


async def missing_resume_choice(page) -> Optional[Dict]:
    """A resume list with nothing selected. The filenames are the choices."""
    for radios in (await _radio_groups(page)).values():
        try:
            labels = []
            checked = False
            for radio in radios:
                if await radio.is_checked():
                    checked = True
                labels.append(await _radio_option_label(page, radio))
            names = [label for label in labels if label]
            if not names or not all(_is_filename(label) for label in names) or checked:
                continue
            return {
                "question": "Which resume should be used?",
                "kind": "radio",
                "choices": names,
            }
        except Exception:
            continue
    return None
