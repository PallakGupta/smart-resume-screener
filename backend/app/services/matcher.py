"""Semantic resume–job matching via LLM with heuristic fallback."""

from __future__ import annotations

import json
import re
from typing import Any

from app.config import get_settings
from app.models import JobDescription, Resume
from app.prompts import (
    JOB_SKILLS_SYSTEM,
    JOB_SKILLS_USER,
    MATCH_SYSTEM,
    MATCH_USER,
)
from app.services.extractor import loads_list
from app.services.llm import chat_json, chat_json_array, llm_available


def extract_job_skills(title: str, description: str) -> list[str]:
    if llm_available():
        try:
            skills = chat_json_array(
                system=JOB_SKILLS_SYSTEM,
                user=JOB_SKILLS_USER.format(job_title=title, job_description=description[:8000]),
            )
            return [str(s).strip() for s in skills if str(s).strip()][:20]
        except Exception:
            pass
    return _heuristic_job_skills(description)


def score_resume_against_job(
    resume: Resume,
    job: JobDescription,
    *,
    shortlist_min_score: float | None = None,
) -> dict[str, Any]:
    threshold = (
        shortlist_min_score
        if shortlist_min_score is not None
        else get_settings().shortlist_min_score
    )

    if llm_available():
        try:
            result = _score_with_llm(resume, job)
            result["scored_by"] = "llm"
            result["shortlisted"] = float(result["score"]) >= threshold
            return result
        except Exception as exc:
            result = _score_heuristic(resume, job)
            result["scored_by"] = "heuristic"
            result["justification"] = (
                f"{result['justification']} (LLM unavailable: {exc})"
            )
            result["shortlisted"] = float(result["score"]) >= threshold
            return result

    result = _score_heuristic(resume, job)
    result["scored_by"] = "heuristic"
    result["shortlisted"] = float(result["score"]) >= threshold
    return result


def _score_with_llm(resume: Resume, job: JobDescription) -> dict[str, Any]:
    skills = loads_list(resume.skills)
    experience = loads_list(resume.experience)
    education = loads_list(resume.education)
    required = loads_list(job.required_skills)

    structured = {
        "candidate_name": resume.candidate_name,
        "email": resume.email,
        "skills": skills,
        "experience": experience,
        "education": education,
        "summary": resume.summary,
    }

    data = chat_json(
        system=MATCH_SYSTEM,
        user=MATCH_USER.format(
            job_title=job.title,
            company=job.company or "N/A",
            job_description=job.description[:8000],
            required_skills=", ".join(required) if required else "Not specified",
            structured_resume=json.dumps(structured, ensure_ascii=False, indent=2),
            resume_text=(resume.raw_text or "")[:6000],
        ),
        temperature=0.2,
    )
    return _normalize_match(data)


def _score_heuristic(resume: Resume, job: JobDescription) -> dict[str, Any]:
    candidate_skills = {s.lower().strip() for s in loads_list(resume.skills)}
    required = [s.lower().strip() for s in loads_list(job.required_skills)]
    if not required:
        required = _heuristic_job_skills(job.description)

    required_set = set(required)
    if not required_set and not candidate_skills:
        return {
            "score": 5.0,
            "justification": (
                "Limited structured skill data available; assigned a neutral baseline "
                "score. Configure OPENAI_API_KEY for semantic LLM scoring."
            ),
            "strengths": [],
            "gaps": ["Insufficient skill data for precise matching"],
        }

    # Soft token overlap against full JD + skills list
    resume_blob = " ".join(
        [
            resume.raw_text or "",
            " ".join(loads_list(resume.skills)),
            resume.summary or "",
        ]
    ).lower()

    matched: list[str] = []
    missing: list[str] = []
    for skill in required:
        if skill in candidate_skills or _skill_mentioned(skill, resume_blob):
            matched.append(skill)
        else:
            missing.append(skill)

    denom = max(len(required), 1)
    coverage = len(matched) / denom
    # Map coverage 0–1 → score ~2–9
    score = round(2 + coverage * 7, 1)
    score = max(1.0, min(10.0, score))

    strengths = [f"Matched skill: {s}" for s in matched[:5]]
    gaps = [f"Missing / unclear: {s}" for s in missing[:5]]
    justification = (
        f"Heuristic skill overlap covering {len(matched)}/{len(required)} required "
        f"skills ({coverage:.0%}). "
        + (
            f"Strong overlap on: {', '.join(matched[:5])}."
            if matched
            else "Little direct skill overlap detected."
        )
        + (
            f" Notable gaps: {', '.join(missing[:5])}."
            if missing
            else " No major required-skill gaps detected."
        )
        + " Enable an LLM API key for richer semantic scoring and narrative justification."
    )

    return {
        "score": score,
        "justification": justification,
        "strengths": strengths,
        "gaps": gaps,
    }


def _heuristic_job_skills(description: str) -> list[str]:
    from app.services.extractor import SKILL_KEYWORDS

    lower = description.lower()
    return [kw for kw in SKILL_KEYWORDS if kw in lower][:20]


def _skill_mentioned(skill: str, blob: str) -> bool:
    # Word-boundary-ish match; handle multi-word skills
    pattern = r"(?<!\w)" + re.escape(skill) + r"(?!\w)"
    return bool(re.search(pattern, blob, flags=re.IGNORECASE))


def _normalize_match(data: dict[str, Any]) -> dict[str, Any]:
    try:
        score = float(data.get("score", 5))
    except (TypeError, ValueError):
        score = 5.0
    score = max(1.0, min(10.0, score))

    strengths = data.get("strengths") or []
    gaps = data.get("gaps") or []
    if not isinstance(strengths, list):
        strengths = [str(strengths)]
    if not isinstance(gaps, list):
        gaps = [str(gaps)]

    justification = str(data.get("justification") or "No justification provided.").strip()

    return {
        "score": score,
        "justification": justification,
        "strengths": [str(s) for s in strengths][:8],
        "gaps": [str(g) for g in gaps][:8],
    }


__all__ = [
    "score_resume_against_job",
    "extract_job_skills",
]