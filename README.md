# Smart Resume Screener

Intelligently parse PDF/text resumes, extract structured candidate data, and score fit against job descriptions with an LLM — then surface a ranked shortlist with clear justification.

![Python](https://img.shields.io/badge/Python-3.11+-3776AB?logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-0.115-009688?logo=fastapi&logoColor=white)
![SQLite](https://img.shields.io/badge/SQLite-Storage-003B57?logo=sqlite&logoColor=white)

## Features

- **Resume ingestion** — PDF, TXT, or MD upload with text extraction
- **Structured extraction** — skills, experience, education, contact fields (LLM + heuristic fallback)
- **Job descriptions** — store JDs; optional required-skills list (auto-inferred if omitted)
- **Semantic matching** — LLM scores candidates **1–10** with strengths, gaps, and narrative justification
- **Shortlist view** — dashboard ranks candidates and flags those above a configurable threshold
- **Persistent storage** — SQLite (swap to Postgres via `DATABASE_URL`)

## Architecture

```
┌──────────────────┐     POST /api/resumes      ┌─────────────────────────────┐
│  Dashboard (SPA) │ ─────────────────────────► │  FastAPI backend             │
│  frontend/       │     POST /api/jobs         │  ├── parser (PDF/text)       │
│                  │     POST /api/screen       │  ├── extractor (LLM/heuristic)│
└──────────────────┘ ◄───────────────────────── │  ├── matcher (score 1–10)    │
         ▲                                       │  └── SQLAlchemy + SQLite     │
         │ static /                              └──────────────┬──────────────┘
         └─────────────────────────────────────────────────────┘
                                                                │
                                                     ┌──────────▼──────────┐
                                                     │ OpenAI-compatible   │
                                                     │ Chat Completions    │
                                                     └─────────────────────┘
```

| Layer | Responsibility |
|--------|----------------|
| `frontend/` | Upload UI, JD form, screening controls, shortlist cards |
| `backend/app/routers/` | REST endpoints for resumes, jobs, screening |
| `backend/app/services/parser.py` | Raw text from PDF/TXT |
| `backend/app/services/extractor.py` | Structured fields from resume text |
| `backend/app/services/matcher.py` | Fit score + justification |
| `backend/app/prompts.py` | All LLM prompt templates |
| `backend/app/models.py` | Resume, JobDescription, MatchResult |

## Quick start

```bash
# 1. Clone
git clone https://github.com/<you>/smart-resume-screener.git
cd smart-resume-screener/backend

# 2. Virtualenv + deps
python -m venv .venv

# Windows
.venv\Scripts\activate
# macOS / Linux
source .venv/bin/activate

pip install -r requirements.txt

# 3. Configure LLM (optional but recommended)
copy .env.example .env   # Windows
# cp .env.example .env   # macOS / Linux
# Edit .env and set OPENAI_API_KEY=sk-...

# 4. Run API + dashboard
python run.py
```

Open **http://localhost:8000** for the dashboard and **http://localhost:8000/docs** for interactive API docs.

> Without an API key the app still works using **heuristic skill overlap**. Scores and justifications are richer with an LLM key.

### Sample resumes

Use the files under `samples/` to try the flow end-to-end:

1. Upload `samples/alex_rivera.txt`, `jordan_lee.txt`, `sam_patel.txt`
2. Create a job (example JD below)
3. Click **Run screening**

**Example job title:** Backend Engineer (LLM products)

**Example description:**

```text
We need a backend engineer to build APIs that power AI recruiting tools.
Requirements: strong Python, FastAPI or Django, SQL/PostgreSQL, Docker,
and experience integrating LLMs (OpenAI or similar). Nice to have: AWS,
Kubernetes, Redis, and prior work on search or ranking systems.
```

## API overview

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/api/health` | Health + whether LLM is configured |
| `POST` | `/api/resumes` | Upload resume (`multipart/form-data` file) |
| `GET` | `/api/resumes` | List parsed resumes |
| `GET` | `/api/resumes/{id}` | Resume detail including raw text |
| `DELETE` | `/api/resumes/{id}` | Delete resume |
| `POST` | `/api/jobs` | Create job description |
| `GET` | `/api/jobs` | List jobs |
| `POST` | `/api/screen` | Score resumes against a job |
| `GET` | `/api/screen/shortlist/{job_id}` | Shortlisted matches only |
| `GET` | `/api/screen/results?job_id=&shortlisted_only=` | Query stored matches |

### Screen request body

```json
{
  "job_id": 1,
  "resume_ids": null,
  "shortlist_min_score": 6.0
}
```

`resume_ids: null` screens **all** stored resumes.

## LLM prompts

All prompts live in [`backend/app/prompts.py`](backend/app/prompts.py).

### 1. Structured extraction

**System:** expert recruiter/parser; return JSON only; do not invent facts.

**User (abbreviated):** parse the resume into:

```json
{
  "candidate_name": "...",
  "email": "...",
  "phone": "...",
  "skills": ["..."],
  "experience": [{ "title", "company", "duration", "description" }],
  "education": [{ "degree", "institution", "year" }],
  "summary": "..."
}
```

### 2. Semantic match scoring (core deliverable)

**System rubric:**

| Score | Meaning |
|------:|---------|
| 1–3 | Poor fit — major gaps |
| 4–5 | Weak fit — some overlap |
| 6–7 | Good fit — meets most requirements |
| 8–9 | Strong fit — clearly qualified |
| 10 | Exceptional / rare |

**User prompt pattern:**

> Compare the following resume with this job description and rate fit on 1–10 with justification.

Returns:

```json
{
  "score": 7.5,
  "justification": "3–5 sentences with concrete evidence…",
  "strengths": ["..."],
  "gaps": ["..."]
}
```

### 3. Job skill inference

When the client omits `required_skills`, the matcher asks the LLM for a JSON array of up to 20 skills (heuristic keyword pass if LLM is off).

## Configuration

| Variable | Default | Purpose |
|----------|---------|---------|
| `OPENAI_API_KEY` | empty | Enables LLM extraction & scoring |
| `OPENAI_BASE_URL` | `https://api.openai.com/v1` | Compatible gateways / Azure-style proxies |
| `OPENAI_MODEL` | `gpt-4o-mini` | Chat model name |
| `DATABASE_URL` | `sqlite:///./data/screener.db` | DB connection string |
| `SHORTLIST_MIN_SCORE` | `6.0` | Default shortlist cutoff |

## Project layout

```
smart-resume-screener/
├── backend/
│   ├── app/
│   │   ├── main.py
│   │   ├── config.py
│   │   ├── database.py
│   │   ├── models.py
│   │   ├── schemas.py
│   │   ├── prompts.py
│   │   ├── routers/
│   │   └── services/
│   ├── requirements.txt
│   ├── .env.example
│   └── run.py
├── frontend/
│   ├── index.html
│   └── assets/
├── samples/
└── README.md
```

## Design choices

- **Heuristic fallback** keeps demos and CI usable without paid API credits
- **JSON-mode prompting** + robust parse helpers reduce brittle free-text failure
- **Upsert match results** so re-screening a JD refreshes scores instead of duplicating rows
- **SQLite by default** for zero-ops local setup; `DATABASE_URL` supports Postgres later

## License

MIT
