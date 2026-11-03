from src.Agent.job_scorer import expand_grouped_skill, score_job


def test_expand_grouped_skill_splits_members():
    assert expand_grouped_skill("AI Tools (ChatGPT, Claude, Gemini)") == ["ChatGPT", "Claude", "Gemini"]


def test_expand_grouped_skill_plain_skill():
    assert expand_grouped_skill("Figma") == ["Figma"]


def test_perfect_match_scores_100():
    job = {"title": "Senior Product Designer", "description": "Product designer who uses Figma and Sketch."}

    assert score_job(job, ["Product Designer"], ["Figma", "Sketch"]) == 100


def test_no_match_scores_0():
    job = {"title": "Accountant", "description": "Ledgers and audits."}

    assert score_job(job, ["Product Designer"], ["Figma"]) == 0


def test_title_only_match_scores_30():
    job = {"title": "Product Designer", "description": "Nothing relevant here."}

    assert score_job(job, ["product designer"], ["Figma"]) == 30


def test_partial_skill_match_is_proportional():
    job = {"title": "Other", "description": "We use Figma."}

    # 1 of 2 skills matched: half of the 30% skills weight and half of the 25% description weight.
    assert score_job(job, ["Product Designer"], ["Figma", "Sketch"]) == round(15 + 12.5)


def test_grouped_skill_matches_any_member():
    job = {"title": "Other", "description": "Experience with Claude is a plus."}

    assert score_job(job, [], ["AI Tools (ChatGPT, Claude)"]) == 55


def test_empty_roles_and_skills():
    job = {"title": "Anything", "description": "Anything"}

    assert score_job(job, [], []) == 0
