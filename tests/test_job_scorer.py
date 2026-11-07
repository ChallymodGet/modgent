from src.Agent.job_scorer import contains_term, expand_grouped_skill, score_job


def test_expand_grouped_skill_splits_members():
    assert expand_grouped_skill("AI Tools (ChatGPT, Claude, Gemini)") == ["ChatGPT", "Claude", "Gemini"]


def test_expand_grouped_skill_plain_skill():
    assert expand_grouped_skill("Figma") == ["Figma"]


def test_contains_term_matches_whole_words_only():
    assert contains_term("Strong UI craft", "ui")
    assert not contains_term("You will build things", "UI")
    assert contains_term("Experience with C++ and Node.js", "c++")
    assert contains_term("Experience with C++ and Node.js", "Node.js")
    assert not contains_term("anything", "")


def test_perfect_match_scores_100():
    job = {"title": "Senior Product Designer", "description": "Product designer who uses Figma and Sketch."}

    assert score_job(job, ["Product Designer"], ["Figma", "Sketch"]) == 100


def test_no_match_scores_0():
    job = {"title": "Accountant", "description": "Ledgers and audits."}

    assert score_job(job, ["Product Designer"], ["Figma"]) == 0


def test_title_only_match_scores_30():
    job = {"title": "Product Designer", "description": "Nothing relevant here."}

    assert score_job(job, ["product designer"], ["Figma"]) == 30


def test_matching_the_strongest_skill_beats_matching_a_weaker_one():
    skills = ["Figma", "Sketch"]  # most-used first
    strongest = score_job({"title": "Other", "description": "We use Figma."}, [], skills)
    weaker = score_job({"title": "Other", "description": "We use Sketch."}, [], skills)

    # Coverage is 15 either way; core strength is 2/3 or 1/3 of 25.
    assert strongest == round(15 + 25 * 2 / 3)
    assert weaker == round(15 + 25 * 1 / 3)


def test_substring_does_not_count_as_a_skill():
    job = {"title": "Other", "description": "You will build dashboards."}

    assert score_job(job, [], ["UI"]) == 0


def test_grouped_skill_matches_any_member():
    job = {"title": "Other", "description": "Experience with Claude is a plus."}

    assert score_job(job, [], ["AI Tools (ChatGPT, Claude)"]) == 55


def test_empty_roles_and_skills():
    job = {"title": "Anything", "description": "Anything"}

    assert score_job(job, [], []) == 0
