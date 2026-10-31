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

def score_job(job, roles, core_skills):

    normalized_roles = []

    for role in roles:
        normalized_roles.append(role.lower().strip())

    normalized_skills = []

    for skill in core_skills:
        normalized_skills.append(skill.lower().strip())

    job_title = job["title"].lower()
    description = job["description"].lower()

    # TITLE — 30%
    title_matches = 0

    for role in normalized_roles:
        if role in job_title:
            title_matches += 1

    if title_matches > 0:
        title_score = 30
    else:
        title_score = 0

    # SKILLS — 30%
    matched_skills = 0

    for skill in normalized_skills:
        expanded = expand_grouped_skill(skill)
        found = any(member.lower() in description for member in expanded)
        if found:
            matched_skills += 1

    if len(normalized_skills) > 0:
        skills_score = (matched_skills / len(normalized_skills)) * 30
    else:
        skills_score = 0

    # DESCRIPTION — 25%
    description_matches = 0

    for skill in normalized_skills:
        expanded = expand_grouped_skill(skill)
        found = any(member.lower() in description for member in expanded)
        if found:
            description_matches += 1

    if len(normalized_skills) > 0:
        description_score = (
            description_matches / len(normalized_skills)
        ) * 25
    else:
        description_score = 0

    # ROLE RELEVANCE — 15%
    role_matches_in_description = 0

    for role in normalized_roles:
        if role in description:
            role_matches_in_description += 1

    if role_matches_in_description > 0:
        relevance_score = 15
    else:
        relevance_score = 0

    total_score = (
        title_score
        + skills_score
        + description_score
        + relevance_score
    )

    return round(total_score)
