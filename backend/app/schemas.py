"""Pydantic request/response schemas."""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class ExperienceItem(BaseModel):
    title: str | None = None
    company: str | None = None
    duration: str | None = None
    description: str | None = None


class EducationItem(BaseModel):
    degree: str | None = None
    institution: str | None = None
    year: str | None = None


class ResumeOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    original_filename: str
    candidate_name: str | None = None
    email: str | None = None
    phone: str | None = None
    skills: list[str] = Field(default_factory=list)
    experience: list[dict[str, Any]] = Field(default_factory=list)
    education: list[dict[str, Any]] = Field(default_factory=list)
    summary: str | None = None
    created_at: datetime | None = None


class ResumeDetail(ResumeOut):
    raw_text: str = ""


class JobCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=256)
    company: str | None = None
    description: str = Field(..., min_length=20)
    required_skills: list[str] = Field(default_factory=list)


class JobOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    company: str | None = None
    description: str
    required_skills: list[str] = Field(default_factory=list)
    created_at: datetime | None = None


class ScreenRequest(BaseModel):
    job_id: int
    resume_ids: list[int] | None = None  # None = all resumes
    shortlist_min_score: float | None = Field(default=None, ge=1, le=10)


class MatchOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    resume_id: int
    job_id: int
    score: float
    justification: str
    strengths: list[str] = Field(default_factory=list)
    gaps: list[str] = Field(default_factory=list)
    shortlisted: bool
    scored_by: str
    candidate_name: str | None = None
    candidate_email: str | None = None
    candidate_skills: list[str] = Field(default_factory=list)
    resume_filename: str | None = None
    created_at: datetime | None = None


class ScreenResponse(BaseModel):
    job_id: int
    job_title: str
    total_screened: int
    shortlisted_count: int
    shortlist_min_score: float
    results: list[MatchOut]


class HealthOut(BaseModel):
    status: str
    llm_configured: bool
    model: str
