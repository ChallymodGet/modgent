import pdfplumber


def extract_cv_text(path):
    full_text = ""

    with pdfplumber.open(path) as pdf:
        for page in pdf.pages:
            page_text = page.extract_text()
            if page_text:
                full_text += page_text + "\n"

    return full_text


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Usage: python -m Agent.read_cv <path-to-cv.pdf>")
        raise SystemExit(1)

    cv_text = extract_cv_text(sys.argv[1])

    print("EXTRACTED CV TEXT:\n")
    print(cv_text)

    print(f"\n\nTotal characters extracted: {len(cv_text)}")