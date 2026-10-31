import re
from .read_cv import extract_cv_text

AI_TOOL_GROUP = {
    "AI Tools": [
        "ChatGPT", "Claude", "Gemini", "Relume", "Stitch", "Figma AI",
        "AI-Assisted UX Research", "AI Prompt Engineering", "Rapid AI-Powered Ideation",
    ]
}


def extract_section(text, section_name, next_section_names):
    """
    Finds a section by its header (e.g. "CORE COMPETENCIES") and returns
    only the text between it and whichever next section header comes first.
    """
    start_match = re.search(re.escape(section_name), text)
    if not start_match:
        return ""

    start_index = start_match.end()

    end_index = len(text)
    for next_name in next_section_names:
        next_match = re.search(re.escape(next_name), text[start_index:])
        if next_match:
            candidate_end = start_index + next_match.start()
            if candidate_end < end_index:
                end_index = candidate_end

    return text[start_index:end_index]

def split_respecting_parentheses(text):
    """
    Splits text on commas, but ignores commas that fall inside parentheses,
    so items like "FinTech (KYC, 2FA, Payments)" stay as one item instead
    of being torn apart at every internal comma.
    """
    parts = []
    current = ""
    depth = 0

    for char in text:
        if char == "(":
            depth += 1
            current += char
        elif char == ")":
            depth -= 1
            current += char
        elif char == "," and depth == 0:
            parts.append(current)
            current = ""
        else:
            current += char

    if current:
        parts.append(current)

    return parts

def extract_bullet_items(section_text, exclude_labels=None):
    """
    Splits a section into individual bullet blocks using the "●" marker,
    joins each bullet's wrapped lines back into one continuous string,
    and splits on commas (respecting parentheses). If a bullet's label
    (the text before the colon) matches one in exclude_labels, its items
    are skipped entirely — used to keep domain tags out of the skills list.
    """
    items = []

    bullets = section_text.split("●")

    for bullet in bullets:
        bullet = bullet.strip()

        if not bullet:
            continue

        joined = " ".join(
            line.strip() for line in bullet.split("\n") if line.strip()
        )

        label = ""
        content = joined

        if ":" in joined:
            label, content = joined.split(":", 1)
            label = label.strip()

        if exclude_labels and label in exclude_labels:
            continue

        parts = split_respecting_parentheses(content)

        for part in parts:
            cleaned = part.strip().strip(".")
            if cleaned:
                items.append(cleaned)

    return items

def extract_labeled_items(section_text, target_label):
    """
    Like extract_bullet_items, but only returns items from the bullet
    whose label matches target_label exactly (e.g. "Domain Expertise").
    """
    items = []

    bullets = section_text.split("●")

    for bullet in bullets:
        bullet = bullet.strip()

        if not bullet:
            continue

        joined = " ".join(
            line.strip() for line in bullet.split("\n") if line.strip()
        )

        if ":" not in joined:
            continue

        label, content = joined.split(":", 1)
        label = label.strip()

        if label != target_label:
            continue

        parts = split_respecting_parentheses(content)

        for part in parts:
            cleaned = part.strip().strip(".")
            if cleaned:
                items.append(cleaned)

    return items

def dedupe_preserve_order(items):
    seen = set()
    result = []
    for item in items:
        key = item.lower()
        if key not in seen:
            seen.add(key)
            result.append(item)
    return result


def extract_hyperlinks(pdf_path):
    """
    Extracts real hyperlinks (LinkedIn, portfolio, email) from the CV's
    PDF annotations — these aren't part of the visible text, so regex on
    cv_text can't find them. Identifies each link by checking its URI.
    """
    import pdfplumber

    links = {
        "linkedin_url": "",
        "portfolio_url": ""
    }

    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            for link in page.hyperlinks:
                uri = link.get("uri", "")

                if "linkedin.com" in uri:
                    links["linkedin_url"] = uri
                elif "behance.net" in uri or "portfolio" in uri.lower():
                    links["portfolio_url"] = uri

    return links


def extract_country_from_location(location_text):
    """
    Pulls a recognizable country name out of a free-text location string
    like "Lagos, Nigeria (Open to Remote & Relocation)". Only returns a
    country from a small known list, rather than guessing — if nothing
    recognizable is found, returns None so the caller can leave it for
    manual review instead of picking wrong.
    """
    known_countries = [
        "Nigeria", "United States", "United Kingdom", "Canada",
        "Germany", "France", "India", "South Africa", "Kenya", "Ghana"
    ]

    for country in known_countries:
        if country.lower() in location_text.lower():
            return country

    return None

def extract_contact_info(cv_text, pdf_path):
    """
    Pulls structured contact details: name, email, phone, location from
    text, plus linkedin/portfolio URLs from the PDF's actual hyperlinks.
    """
    lines = [line.strip() for line in cv_text.split("\n") if line.strip()]

    name = lines[0] if lines else ""

    email_match = re.search(r'[\w\.-]+@[\w\.-]+\.\w+', cv_text)
    email = email_match.group(0) if email_match else ""

    phone_match = re.search(r'\+?\d[\d\s\-]{7,}\d', cv_text)
    phone = phone_match.group(0).strip() if phone_match else ""

    location = ""
    for line in lines[:5]:
        if "," in line and "@" not in line and not any(char.isdigit() for char in line):
            location = line
            break

    hyperlinks = extract_hyperlinks(pdf_path)

    contact = {
        "name": name,
        "email": email,
        "phone": phone,
        "location": location,
        "linkedin_url": hyperlinks["linkedin_url"],
        "portfolio_url": hyperlinks["portfolio_url"],
        "country": extract_country_from_location(location)
    }

    return contact

def build_candidate_summary(cv_text):
    """
    Builds a compact, human-readable summary of the candidate's background
    for use in AI-generated answers — pulled from the CV's own SUMMARY and
    CAREER HIGHLIGHTS sections, since that's where the candidate already
    described themselves in their own words.
    """
    summary_section = extract_section(
        cv_text,
        "SUMMARY",
        ["CAREER HIGHLIGHTS"]
    )

    highlights_section = extract_section(
        cv_text,
        "CAREER HIGHLIGHTS",
        ["CORE COMPETENCIES"]
    )

    summary_text = " ".join(
        line.strip() for line in summary_section.split("\n") if line.strip()
    )

    highlight_lines = []
    for bullet in highlights_section.split("●"):
        bullet = bullet.strip()
        if not bullet:
            continue
        joined = " ".join(
            line.strip() for line in bullet.split("\n") if line.strip()
        )
        if joined:
            highlight_lines.append(joined)

    combined = summary_text

    if highlight_lines:
        combined += "\n\nKey achievements:\n"
        for highlight in highlight_lines[:4]:
            combined += f"- {highlight}\n"

    return combined.strip()

def build_candidate_profile(cv_text, pdf_path):
    contact = extract_contact_info(cv_text, pdf_path)

    competencies_section = extract_section(
        cv_text,
        "CORE COMPETENCIES",
        ["EDUCATION"]
    )

    tools_section = extract_section(
        cv_text,
        "TOOLS & TECHNOLOGIES",
        ["CERTIFICATION"]
    )

    skills = dedupe_preserve_order(
        extract_bullet_items(competencies_section, exclude_labels=["Domain Expertise"])
    )
    domains = dedupe_preserve_order(
        extract_labeled_items(competencies_section, "Domain Expertise")
    )
    tools = dedupe_preserve_order(extract_bullet_items(tools_section))

    candidate = {
        "contact": contact,
        "skills": skills,
        "domains": domains,
        "tools": tools
    }

    return candidate


def rank_skills_by_cv_frequency(cv_text, skills, top_n=15, groups=None):
    """
    Ranks skills by how often they appear across the CV.
    If `groups` is provided (a dict like {"AI Tools": ["ChatGPT", "Claude", "Gemini"]}),
    each group's members are combined into a single counted entry using their
    combined mention count, displayed as "AI Tools (ChatGPT, Claude, Gemini)"
    instead of each member taking its own ranking slot.
    """
    cv_text_lower = cv_text.lower()

    grouped_member_lookup = set()
    counts = {}

    if groups:
        for group_name, members in groups.items():
            total = 0
            matched_members = []

            for member in members:
                member_count = cv_text_lower.count(member.lower())
                total += member_count
                grouped_member_lookup.add(member.lower())

                if member_count > 0:
                    matched_members.append(member)

            if matched_members:
                display_name = f"{group_name} ({', '.join(matched_members)})"
            else:
                display_name = group_name

            counts[display_name] = total

    for skill in skills:
        if skill.lower() in grouped_member_lookup:
            continue
        counts[skill] = cv_text_lower.count(skill.lower())

    sorted_items = sorted(counts.items(), key=lambda pair: pair[1], reverse=True)

    top_skills = [name for name, count in sorted_items[:top_n]]

    return top_skills


def build_skills_from_cv(cv_path, top_n=15):
    """
    CANDIDATE PROFILE stage — extracts and ranks skills from a CV file.
    Used by the discovery pipeline to score scraped jobs against the
    candidate's actual background instead of a fixed/placeholder score.
    """
    cv_text = extract_cv_text(cv_path)
    candidate_profile = build_candidate_profile(cv_text, cv_path)

    all_skills = dedupe_preserve_order(
        candidate_profile["skills"] + candidate_profile["tools"]
    )

    return rank_skills_by_cv_frequency(
        cv_text, all_skills, top_n=top_n, groups=AI_TOOL_GROUP
    )


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Usage: python -m Agent.parse_cv <path-to-cv.pdf>")
        raise SystemExit(1)

    debug_cv_path = sys.argv[1]
    cv_text = extract_cv_text(debug_cv_path)

    profile = build_candidate_profile(cv_text, debug_cv_path)

    print("SKILLS FOUND:\n")
    for skill in profile["skills"]:
        print(f"- {skill}")

    print(f"\nTotal skills: {len(profile['skills'])}")

    print("\n\nDOMAINS FOUND:\n")
    for domain in profile["domains"]:
        print(f"- {domain}")

    print(f"\nTotal domains: {len(profile['domains'])}")

    print("\n\nTOOLS FOUND:\n")
    for tool in profile["tools"]:
        print(f"- {tool}")

    print(f"\nTotal tools: {len(profile['tools'])}")

    combined_skills = dedupe_preserve_order(profile["skills"] + profile["tools"])

    core_skills = rank_skills_by_cv_frequency(
        cv_text,
        combined_skills,
        top_n=15,
        groups=AI_TOOL_GROUP
    )

    print("\n\nTOP 15 CORE SKILLS (by CV frequency):\n")
    for skill in core_skills:
        print(f"- {skill}")

    print("\n\nCONTACT INFO:\n")
    for key, value in profile["contact"].items():
        print(f"{key}: {value}")