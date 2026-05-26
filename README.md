# AI Resume Screening System

A Streamlit app for ranking resumes against a job description.

## Features

- Upload multiple TXT, PDF, or DOCX resumes.
- Paste or edit a job description.
- Set required skills and minimum experience.
- Rank candidates with skill, keyword, and experience scores.
- Download a CSV screening report.

## Run

```powershell
.venv\Scripts\pip.exe install -r requirements.txt
.venv\Scripts\streamlit.exe run app.py
```

The app uses local text analysis, so it does not need an API key.
