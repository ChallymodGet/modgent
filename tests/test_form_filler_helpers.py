import pytest

from src.Agent.form_filler import (
    _is_dial_code_list,
    _letter_is_dump,
    _safe_upload_name,
    desired_field_value,
    find_learned_answer,
    is_protected_field,
    match_field_to_value,
    match_recurring_question,
    question_key,
    questions_match,
)

CONTACT = {
    "name": "Ada Lovelace",
    "email": "ada@example.com",
    "phone": "+10000000000",
    "linkedin_url": "https://linkedin.com/in/ada",
    "portfolio_url": "https://ada.example.com",
    "location": "London",
    "country": "United Kingdom",
}

RECURRING = {
    "work_authorization": "Yes",
    "sponsorship_required": "No",
    "how_heard": "LinkedIn",
    "non_compete": "No",
    "willing_to_relocate": "Open",
    "years_experience": "5",
    "salary_expectation": "Negotiable",
}


@pytest.mark.parametrize("field", ["race", "gender identity", "veteran status", "voluntary self-identification"])
def test_protected_fields_are_never_filled(field):
    assert is_protected_field(field)
    assert match_field_to_value(field, CONTACT) is None
    assert desired_field_value(field, CONTACT, RECURRING, {field: "x"}) is None


@pytest.mark.parametrize(
    "field, expected",
    [
        ("email address", "ada@example.com"),
        ("phone number", "+10000000000"),
        ("linkedin profile", "https://linkedin.com/in/ada"),
        ("portfolio", "https://ada.example.com"),
        ("first name", "Ada"),
        ("last name", "Lovelace"),
        ("full name", "Ada Lovelace"),
        ("name", "Ada Lovelace"),
        ("country", "United Kingdom"),
        ("city", "London"),
        ("resume", "__UPLOAD_CV__"),
        ("upload cv", "__UPLOAD_CV__"),
        ("first_name", "Ada"),
    ],
)
def test_match_field_to_value(field, expected):
    assert match_field_to_value(field, CONTACT) == expected


def test_tell_is_not_a_phone_field():
    assert match_field_to_value("tell us about yourself", CONTACT) is None


def test_last_name_needs_two_name_parts():
    assert match_field_to_value("last name", {"name": "Ada"}) is None


@pytest.mark.xfail(strict=True, reason="'state' substring matches 'statement' and fills the location")
def test_personal_statement_is_not_a_location_field():
    assert match_field_to_value("personal statement", CONTACT) is None


@pytest.mark.parametrize(
    "field, expected",
    [
        ("are you authorized to work in the us", "Yes"),
        ("will you require sponsorship", "No"),
        ("how did you hear about us", "LinkedIn"),
        ("are you willing to relocate", "Open"),
        ("years of experience", "5"),
        ("expected salary", "Negotiable"),
        ("favourite colour", None),
    ],
)
def test_match_recurring_question(field, expected):
    assert match_recurring_question(field, RECURRING) == expected


@pytest.mark.xfail(strict=True, reason="any question containing 'experience' gets years_experience")
def test_open_ended_experience_question_is_not_years_of_experience():
    assert match_recurring_question("describe your experience with design systems", RECURRING) is None


def test_question_key_normalises_case_and_spacing():
    assert question_key("  Why   Do You\nWant This Job? ") == "why do you want this job?"
    assert question_key(None) == ""


def test_questions_match():
    assert questions_match("Why do you want this job?", "why do you  want this job?")
    assert questions_match("Why do you want this job", "Why do you want this job? (300 words)")
    assert not questions_match("Name", "Name of your school")  # too short for a contained match
    assert not questions_match("", "anything")


def test_find_learned_answer():
    learned = {"what is your notice period": "Two weeks"}

    assert find_learned_answer("What is your notice period?", learned) == "Two weeks"
    assert find_learned_answer("what is your notice period", learned) == "Two weeks"
    assert find_learned_answer("start date", learned) is None
    assert find_learned_answer("what is your notice period", {}) is None


def test_desired_field_value_priority():
    learned = {"how did you hear about us": "A friend"}

    # Recurring answers win over learned ones; learned ones fill the gaps.
    assert desired_field_value("how did you hear about us", CONTACT, RECURRING, learned) == "LinkedIn"
    assert desired_field_value("how did you hear about us", CONTACT, None, learned) == "A friend"
    # The CV upload marker is never returned as a typed value.
    assert desired_field_value("resume", CONTACT, RECURRING, {}) is None


def test_dial_code_list_detection():
    dial_codes = [f"Country{i} +{200 + i}" for i in range(10)]
    real_options = ["Yes", "No", "Prefer not to say"] * 4

    assert _is_dial_code_list(dial_codes)
    assert not _is_dial_code_list(real_options)
    assert not _is_dial_code_list(dial_codes[:5])  # too few to judge


@pytest.mark.parametrize(
    "text, is_dump",
    [
        ("", True),
        ("Ada Lovelace | ada@example.com", True),
        ("Call me on +2348012345678", True),
        ("Summary: designer. LinkedIn: ada", True),
        ("Dear Hiring Manager,\n\nI am excited to apply for this role.", False),
    ],
)
def test_letter_is_dump(text, is_dump):
    assert _letter_is_dump(text) is is_dump


def test_safe_upload_name():
    assert _safe_upload_name("Ada CV (2026).pdf", "cv_123.pdf") == "Ada CV (2026).pdf"
    assert _safe_upload_name("../../etc/passwd", "cv_123.pdf") == "passwd"
    assert _safe_upload_name("", "data/cv/cv_123.pdf") == "cv_123.pdf"
    assert _safe_upload_name("bad<>name.pdf", "x.pdf") == "bad name.pdf"
