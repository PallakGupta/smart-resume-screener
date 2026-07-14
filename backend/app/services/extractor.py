"""Heuristic + LLM resume field extraction."""

from __future__ import annotations

import json
import re
from typing import Any

from app.prompts import EXTRACT_SYSTEM, EXTRACT_USER
from app.services.llm import chat_json, llm_available


EMAIL_RE = re.compile(r"[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}")
PHONE_RE = re.compile(
    r"(?:\+?\d{1,3}[\s\-.]?)?(?:\(?\d{2,4}\)?[\s\-.]?)?\d{3}[\s\-.]?\d{4}"
)

SKILL_KEYWORDS = [
    "python", "java", "javascript", "typescript", "go", "golang", "rust", "c++", "c#",
    "react", "angular", "vue", "node.js", "nodejs", "express", "fastapi", "django",
    "flask", "spring", "sql", "postgresql", "mysql", "mongodb", "redis", "elasticsearch",
    "aws", "azure", "gcp", "docker", "kubernetes", "terraform", "jenkins", "ci/cd",
    "git", "linux", "machine learning", "deep learning", "nlp", "pytorch", "tensorflow",
    "pandas", "numpy", "scikit-learn", "spark", "hadoop", "kafka", "graphql", "rest",
    "microservices", "agile", "scrum", "html", "css", "tailwind", "next.js", "svelte",
    "llm", "openai", "langchain", "prompt engineering", "data analysis", "etl",
    "tableau", "power bi", "excel", "communication", "leadership", "project management",
]


def extract_structured(resume_text: str) -> dict[str, Any]:
    """Prefer LLM extraction; fall back to heuristics if LLM is unavailable."""
    if llm_available():
        try:
            return _extract_with_llm(resume_text)
        except Exception:
            pass
    return _extract_heuristic(resume_text)


def _extract_with_llm(resume_text: str) -> dict[str, Any]:
    truncated = resume_text[:12000]
    data = chat_json(
        system=EXTRACT_SYSTEM,
        user=EXTRACT_USER.format(resume_text=truncated),
        temperature=0.1,
    )
    return _normalize_extracted(data, resume_text)


def _extract_heuristic(resume_text: str) -> dict[str, Any]:
    email_match = EMAIL_RE.search(resume_text)
    phone_match = PHONE_RE.search(resume_text)

    lines = [ln.strip() for ln in resume_text.splitlines() if ln.strip()]
    name = None
    for line in lines[:8]:
        if EMAIL_RE.search(line) or PHONE_RE.search(line):
            continue
        if len(line) < 60 and not line.lower().startswith(("http", "www", "linkedin")):
            name = line
            break

    lower = resume_text.lower()
    skills = sorted({kw for kw in SKILL_KEYWORDS if kw in lower}, key=lower.find)

    experience = _section_blobs(resume_text, ("experience", "work history", "employment"))
    education = _section_blobs(resume_text, ("education", "academic", "qualification"))

    return {
        "candidate_name": name,
        "email": email_match.group(0) if email_match else None,
        "phone": phone_match.group(0) if phone_match else None,
        "skills": skills[:30],
        "experience": [{"description": blob} for blob in experience[:5]],
        "education": [{"description": blob} for blob in education[:3]],
        "summary": (lines[0][:280] if lines else None),
    }


def _section_blobs(text: str, headers: tuple[str, ...]) -> list[str]:
    pattern = "|".join(re.escape(h) for h in headers)
    matches = list(re.finditer(rf"(?im)^(?:{pattern})\s*:?\s*$", text))
    if not matches:
        return []

    blobs: list[str] = []
    for i, match in enumerate(matches):
        start = match.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        chunk = text[start:end].strip()
        if chunk:
            blobs.append(chunk[:800])
    return blobs


def _normalize_extracted(data: dict[str, Any], resume_text: str) -> dict[str, Any]:
    if not isinstance(data, dict):
        return _extract_heuristic(resume_text)

    skills = data.get("skills") or []
    if not isinstance(skills, list):
        skills = []
    skills = [str(s).strip() for s in skills if str(s).strip()]

    experience = data.get("experience") or []
    if not isinstance(experience, list):
        experience = []

    education = data.get("education") or []
    if not isinstance(education, list):
        education = []

    email = data.get("email")
    if not email:
        m = EMAIL_RE.search(resume_text)
        email = m.group(0) if m else None

    return {
        "candidate_name": data.get("candidate_name"),
        "email": email,
        "phone": data.get("phone"),
        "skills": skills,
        "experience": experience,
        "education": education,
        "summary": data.get("summary"),
    }


def dumps_list(items: list[Any]) -> str:
    return json.dumps(items, ensure_ascii=False)


def loads_list(raw: str | None) -> list[Any]:
    if not raw:
        return []
    try:
        value = json.loads(raw)
        return value if isinstance(value, list) else []
    except json.JSONDecodeError:
        return []
