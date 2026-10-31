from .ai_generator import generate_answer
from .parse_cv import extract_cv_text, build_candidate_summary


def build_answer_prompt(question, job_title, company, job_description, candidate_summary):
    prompt = f"""You are helping a job applicant answer a question on a job application form.

Job title: {job_title}
Company: {company}

Job description (excerpt):
{job_description[:1000]}

Candidate background:
{candidate_summary}

Application question: "{question}"

Write a concise, professional, first-person answer (2-4 sentences) that directly answers this question, referencing specific, relevant details from the candidate's background where genuinely applicable. Do not invent facts, dates, companies, or experience not mentioned in the candidate background. Do not use generic filler phrases like "I am passionate about" without backing it up with something specific.

Answer:"""

    return prompt


def generate_application_answer(question, job, candidate_summary):
    """
    Generates a draft answer for an open-ended application question, using
    the job's context and the candidate's actual background. This is a
    DRAFT ONLY — always meant to be reviewed and edited by the human before
    it's ever submitted anywhere.
    """
    prompt = build_answer_prompt(
        question=question,
        job_title=job.get("title", ""),
        company=job.get("company", ""),
        job_description=job.get("description", ""),
        candidate_summary=candidate_summary
    )

    answer = generate_answer(prompt, max_tokens=200)

    return answer


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Usage: python -m Agent.answer_generator <path-to-cv.pdf>")
        raise SystemExit(1)

    cv_text = extract_cv_text(sys.argv[1])
    candidate_summary = build_candidate_summary(cv_text)

    print("=== CANDIDATE SUMMARY (from your real CV) ===\n")
    print(candidate_summary)

    test_job = {
        "title": "Senior Product Designer",
        "company": "Tava Health",
        "description": "We are seeking a Senior Product Designer to lead the design of our patient-facing product experiences, focused on creating intuitive, accessible designs for patient conversion flows, scheduling, payments, and the telehealth experience."
    }

    test_question = "Why are you interested in this role?"

    print("\n\n=== GENERATING ANSWER ===\n")
    result = generate_application_answer(test_question, test_job, candidate_summary)
    print(f"Question: {test_question}\n")
    print(f"Generated answer:\n{result}")