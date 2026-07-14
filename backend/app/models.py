"""ORM models for resumes, job descriptions, and match results."""

from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Resume(Base):
    __tablename__ = "resumes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    filename: Mapped[str] = mapped_column(String(512), nullable=False)
    original_filename: Mapped[str] = mapped_column(String(512), nullable=False)
    raw_text: Mapped[str] = mapped_column(Text, nullable=False, default="")

    candidate_name: Mapped[str | None] = mapped_column(String(256), nullable=True)
    email: Mapped[str | None] = mapped_column(String(256), nullable=True)
    phone: Mapped[str | None] = mapped_column(String(64), nullable=True)
    skills: Mapped[str] = mapped_column(Text, nullable=False, default="[]")  # JSON list
    experience: Mapped[str] = mapped_column(Text, nullable=False, default="[]")  # JSON list
    education: Mapped[str] = mapped_column(Text, nullable=False, default="[]")  # JSON list
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    matches: Mapped[list["MatchResult"]] = relationship(
        back_populates="resume", cascade="all, delete-orphan"
    )


class JobDescription(Base):
    __tablename__ = "job_descriptions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    title: Mapped[str] = mapped_column(String(256), nullable=False)
    company: Mapped[str | None] = mapped_column(String(256), nullable=True)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    required_skills: Mapped[str] = mapped_column(Text, nullable=False, default="[]")  # JSON
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    matches: Mapped[list["MatchResult"]] = relationship(
        back_populates="job", cascade="all, delete-orphan"
    )


class MatchResult(Base):
    __tablename__ = "match_results"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    resume_id: Mapped[int] = mapped_column(ForeignKey("resumes.id", ondelete="CASCADE"))
    job_id: Mapped[int] = mapped_column(
        ForeignKey("job_descriptions.id", ondelete="CASCADE")
    )

    score: Mapped[float] = mapped_column(Float, nullable=False)  # 1–10
    justification: Mapped[str] = mapped_column(Text, nullable=False)
    strengths: Mapped[str] = mapped_column(Text, nullable=False, default="[]")  # JSON
    gaps: Mapped[str] = mapped_column(Text, nullable=False, default="[]")  # JSON
    shortlisted: Mapped[int] = mapped_column(Integer, nullable=False, default=0)  # 0/1
    scored_by: Mapped[str] = mapped_column(String(64), nullable=False, default="llm")

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    resume: Mapped["Resume"] = relationship(back_populates="matches")
    job: Mapped["JobDescription"] = relationship(back_populates="matches")
