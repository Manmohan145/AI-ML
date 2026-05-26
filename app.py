import io
import re
from collections import Counter
from dataclasses import dataclass

import pandas as pd
import streamlit as st

try:
    from PyPDF2 import PdfReader
except ImportError:
    PdfReader = None

try:
    from docx import Document
except ImportError:
    Document = None


STOP_WORDS = {
    "a",
    "an",
    "and",
    "are",
    "as",
    "at",
    "be",
    "by",
    "for",
    "from",
    "has",
    "have",
    "in",
    "is",
    "it",
    "of",
    "on",
    "or",
    "that",
    "the",
    "this",
    "to",
    "with",
    "you",
    "your",
}

DEFAULT_SKILLS = [
    "python",
    "sql",
    "excel",
    "machine learning",
    "deep learning",
    "data analysis",
    "data visualization",
    "streamlit",
    "power bi",
    "tableau",
    "statistics",
    "nlp",
    "aws",
    "azure",
    "git",
    "communication",
    "leadership",
    "project management",
]

SAMPLE_JOB = """We are hiring a data analyst who can work with Python, SQL, Excel, dashboards, statistics, and stakeholder communication. Experience with Streamlit, Power BI, machine learning, and data visualization is a plus."""


@dataclass
class ResumeResult:
    file_name: str
    score: int
    skill_score: int
    keyword_score: int
    experience_score: int
    matched_skills: list[str]
    missing_skills: list[str]
    years_experience: int
    summary: str


def normalize_text(text: str) -> str:
    return re.sub(r"\s+", " ", text.lower()).strip()


def tokenize(text: str) -> list[str]:
    return [
        word
        for word in re.findall(r"[a-zA-Z][a-zA-Z+#.\-]{1,}", normalize_text(text))
        if word not in STOP_WORDS
    ]


def extract_pdf_text(file_bytes: bytes) -> str:
    if PdfReader is None:
        raise RuntimeError("Install PyPDF2 to screen PDF resumes.")

    reader = PdfReader(io.BytesIO(file_bytes))
    return "\n".join(page.extract_text() or "" for page in reader.pages)


def extract_docx_text(file_bytes: bytes) -> str:
    if Document is None:
        raise RuntimeError("Install python-docx to screen DOCX resumes.")

    document = Document(io.BytesIO(file_bytes))
    return "\n".join(paragraph.text for paragraph in document.paragraphs)


def extract_resume_text(uploaded_file) -> str:
    file_bytes = uploaded_file.getvalue()
    file_name = uploaded_file.name.lower()

    if file_name.endswith(".pdf"):
        return extract_pdf_text(file_bytes)
    if file_name.endswith(".docx"):
        return extract_docx_text(file_bytes)
    return file_bytes.decode("utf-8", errors="ignore")


def parse_skills(raw_skills: str) -> list[str]:
    return sorted(
        {
            skill.strip().lower()
            for skill in raw_skills.split(",")
            if skill.strip()
        }
    )


def find_skills(text: str, skills: list[str]) -> list[str]:
    normalized = normalize_text(text)
    matches = []

    for skill in skills:
        pattern = r"(?<![a-zA-Z0-9])" + re.escape(skill) + r"(?![a-zA-Z0-9])"
        if re.search(pattern, normalized):
            matches.append(skill)

    return matches


def estimate_years_experience(text: str) -> int:
    normalized = normalize_text(text)
    year_matches = re.findall(r"(\d{1,2})\+?\s*(?:years|yrs)\s+(?:of\s+)?experience", normalized)
    if year_matches:
        return max(int(match) for match in year_matches)

    date_ranges = re.findall(r"(20\d{2}|19\d{2})\s*[-–]\s*(20\d{2}|present|current)", normalized)
    total_years = 0
    for start, end in date_ranges:
        end_year = 2026 if end in {"present", "current"} else int(end)
        total_years += max(0, end_year - int(start))
    return min(total_years, 30)


def keyword_overlap(job_description: str, resume_text: str) -> tuple[int, list[str]]:
    job_words = Counter(tokenize(job_description))
    resume_words = set(tokenize(resume_text))
    important_words = [word for word, count in job_words.most_common(30) if count > 0]
    matched_words = [word for word in important_words if word in resume_words]

    if not important_words:
        return 0, []

    return round((len(matched_words) / len(important_words)) * 100), matched_words


def build_summary(result: ResumeResult, matched_keywords: list[str]) -> str:
    positives = []
    concerns = []

    if result.matched_skills:
        positives.append("matches " + ", ".join(result.matched_skills[:5]))
    if matched_keywords:
        positives.append("covers job keywords like " + ", ".join(matched_keywords[:5]))
    if result.years_experience:
        positives.append(f"shows about {result.years_experience} years of experience")

    if result.missing_skills:
        concerns.append("missing " + ", ".join(result.missing_skills[:4]))

    summary = "; ".join(positives) if positives else "limited direct overlap with the job description"
    if concerns:
        summary += ". Review note: " + "; ".join(concerns)
    return summary + "."


def score_resume(file_name: str, text: str, job_description: str, skills: list[str], min_years: int) -> ResumeResult:
    matched_skills = find_skills(text, skills)
    missing_skills = [skill for skill in skills if skill not in matched_skills]
    years_experience = estimate_years_experience(text)
    keyword_score, matched_keywords = keyword_overlap(job_description, text)

    skill_score = round((len(matched_skills) / len(skills)) * 100) if skills else 0
    experience_score = 100 if years_experience >= min_years else round((years_experience / max(min_years, 1)) * 100)
    score = round((skill_score * 0.5) + (keyword_score * 0.35) + (experience_score * 0.15))

    result = ResumeResult(
        file_name=file_name,
        score=score,
        skill_score=skill_score,
        keyword_score=keyword_score,
        experience_score=experience_score,
        matched_skills=matched_skills,
        missing_skills=missing_skills,
        years_experience=years_experience,
        summary="",
    )
    result.summary = build_summary(result, matched_keywords)
    return result


st.set_page_config(page_title="AI Resume Screening System", page_icon="search", layout="wide")

with st.sidebar:
    st.title("Resume Screener")
    st.caption("Rank applicants against a role using local text analysis.")
    min_years = st.slider("Minimum experience", min_value=0, max_value=15, value=2)
    pass_score = st.slider("Shortlist score", min_value=0, max_value=100, value=70)

st.title("AI Resume Screening System")
st.write("Upload resumes, compare them with a job description, and shortlist the strongest matches.")

job_description = st.text_area("Job description", value=SAMPLE_JOB, height=150)
skills_input = st.text_area("Required skills, comma separated", value=", ".join(DEFAULT_SKILLS), height=90)
uploaded_files = st.file_uploader(
    "Upload resumes",
    type=["txt", "pdf", "docx"],
    accept_multiple_files=True,
)

skills = parse_skills(skills_input)

if uploaded_files:
    results = []
    errors = []

    for uploaded_file in uploaded_files:
        try:
            resume_text = extract_resume_text(uploaded_file)
            if not resume_text.strip():
                errors.append(f"{uploaded_file.name}: no readable text found.")
                continue
            results.append(score_resume(uploaded_file.name, resume_text, job_description, skills, min_years))
        except Exception as exc:
            errors.append(f"{uploaded_file.name}: {exc}")

    if errors:
        for error in errors:
            st.warning(error)

    if results:
        results.sort(key=lambda item: item.score, reverse=True)
        shortlisted = sum(1 for item in results if item.score >= pass_score)

        metric_cols = st.columns(4)
        metric_cols[0].metric("Resumes Screened", len(results))
        metric_cols[1].metric("Shortlisted", shortlisted)
        metric_cols[2].metric("Top Score", f"{results[0].score}%")
        metric_cols[3].metric("Required Skills", len(skills))

        table_data = [
            {
                "Rank": index + 1,
                "Candidate": result.file_name,
                "Score": result.score,
                "Decision": "Shortlist" if result.score >= pass_score else "Review",
                "Skills": result.skill_score,
                "Keywords": result.keyword_score,
                "Experience": result.experience_score,
                "Years": result.years_experience,
                "Matched Skills": ", ".join(result.matched_skills[:8]),
            }
            for index, result in enumerate(results)
        ]

        st.subheader("Ranked Candidates")
        st.dataframe(pd.DataFrame(table_data), use_container_width=True, hide_index=True)

        csv = pd.DataFrame(table_data).to_csv(index=False).encode("utf-8")
        st.download_button("Download screening report", csv, "resume_screening_report.csv", "text/csv")

        st.subheader("Candidate Notes")
        for result in results:
            with st.expander(f"{result.file_name} - {result.score}%"):
                note_cols = st.columns(3)
                note_cols[0].metric("Skill Match", f"{result.skill_score}%")
                note_cols[1].metric("Keyword Match", f"{result.keyword_score}%")
                note_cols[2].metric("Experience Match", f"{result.experience_score}%")
                st.write(result.summary)
                st.write("Matched skills:", ", ".join(result.matched_skills) or "None")
                st.write("Missing skills:", ", ".join(result.missing_skills) or "None")
else:
    st.info("Upload one or more resumes to begin screening.")

with st.expander("How scoring works"):
    st.write("Final score = 50% required skills, 35% job-description keyword overlap, and 15% experience match.")
    st.write("This tool helps prioritize review. Do not use it as the only basis for hiring decisions.")
