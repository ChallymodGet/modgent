import re


def expand_grouped_skill(skill):
    """
    If a skill string looks like a grouped label — "AI Tools (ChatGPT, Claude, Gemini)" —
    returns the individual member names instead. Otherwise returns the skill as-is,
    as a single-item list.
    """
    match = re.match(r"^(.+?)\s*\((.+)\)$", skill)

    if match:
        members_text = match.group(2)
        members = [m.strip() for m in members_text.split(",")]
        return members

    return [skill]


def contains_term(text, term):
    """
    Whole-word, case-insensitive match. "UI" must not match "build", and
    terms with symbols such as "C++" or "Node.js" still match as written.
    """
    term = term.strip().lower()
    if not term:
        return False
    return re.search(rf"(?<!\w){re.escape(term)}(?!\w)", text.lower()) is not None


def skill_found(skill, description):
    return any(contains_term(description, member) for member in expand_grouped_skill(skill))


def score_job(job, roles, core_skills):
    """
    0–100 keyword match between a listing and the candidate.

    TITLE 30           — a target role appears in the job title.
    SKILL COVERAGE 30  — share of the CV's core skills named in the description.
    CORE STRENGTH 25   — the same matches, weighted by each skill's rank in the
                         CV (core_skills arrive most-used first), so matching
                         the candidate's strongest skills counts for more.
    ROLE RELEVANCE 15  — a target role appears in the description.
    """
    roles = [role.strip() for role in roles if role.strip()]
    skills = [skill.strip() for skill in core_skills if skill.strip()]
    title = job["title"]
    description = job["description"]

    title_score = 30 if any(contains_term(title, role) for role in roles) else 0

    matched = [skill_found(skill, description) for skill in skills]

    coverage_score = (sum(matched) / len(skills)) * 30 if skills else 0

    # Rank weights: first skill weighs n, last weighs 1.
    weights = range(len(skills), 0, -1)
    total_weight = sum(weights)
    strength_score = (
        sum(weight for weight, hit in zip(weights, matched) if hit) / total_weight * 25
        if total_weight else 0
    )

    relevance_score = 15 if any(contains_term(description, role) for role in roles) else 0

    return round(title_score + coverage_score + strength_score + relevance_score)
