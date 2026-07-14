"""Screening / matching endpoints."""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.config import get_settings
from app.database import get_db
from app.models import JobDescription, MatchResult, Resume
from app.schemas import MatchOut, ScreenRequest, ScreenResponse
from app.services.extractor import dumps_list, loads_list
from app.services.matcher import score_resume_against_job

router = APIRouter(prefix="/screen", tags=["screening"])


def _match_out(match: MatchResult, resume: Resume | None = None) -> MatchOut:
    resume = resume or match.resume
    return MatchOut(
        id=match.id,
        resume_id=match.resume_id,
        job_id=match.job_id,
        score=match.score,
        justification=match.justification,
        strengths=loads_list(match.strengths),
        gaps=loads_list(match.gaps),
        shortlisted=bool(match.shortlisted),
        scored_by=match.scored_by,
        candidate_name=resume.candidate_name if resume else None,
        candidate_email=resume.email if resume else None,
        candidate_skills=loads_list(resume.skills) if resume else [],
        resume_filename=resume.original_filename if resume else None,
        created_at=match.created_at,
    )


@router.post("", response_model=ScreenResponse)
def screen_candidates(
    payload: ScreenRequest,
    db: Session = Depends(get_db),
) -> ScreenResponse:
    job = db.get(JobDescription, payload.job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    query = db.query(Resume)
    if payload.resume_ids:
        query = query.filter(Resume.id.in_(payload.resume_ids))
    resumes = query.order_by(Resume.created_at.desc()).all()
    if not resumes:
        raise HTTPException(status_code=400, detail="No resumes to screen")

    threshold = (
        payload.shortlist_min_score
        if payload.shortlist_min_score is not None
        else get_settings().shortlist_min_score
    )

    results: list[MatchOut] = []
    for resume in resumes:
        scored = score_resume_against_job(
            resume, job, shortlist_min_score=threshold
        )

        # Upsert: replace prior result for this resume+job pair
        existing = (
            db.query(MatchResult)
            .filter(
                MatchResult.resume_id == resume.id,
                MatchResult.job_id == job.id,
            )
            .first()
        )
        if existing:
            match = existing
        else:
            match = MatchResult(resume_id=resume.id, job_id=job.id)
            db.add(match)

        match.score = scored["score"]
        match.justification = scored["justification"]
        match.strengths = dumps_list(scored.get("strengths") or [])
        match.gaps = dumps_list(scored.get("gaps") or [])
        match.shortlisted = 1 if scored["shortlisted"] else 0
        match.scored_by = scored["scored_by"]
        db.flush()
        results.append(_match_out(match, resume))

    db.commit()
    results.sort(key=lambda m: m.score, reverse=True)

    shortlisted = [m for m in results if m.shortlisted]
    return ScreenResponse(
        job_id=job.id,
        job_title=job.title,
        total_screened=len(results),
        shortlisted_count=len(shortlisted),
        shortlist_min_score=threshold,
        results=results,
    )


@router.get("/results", response_model=list[MatchOut])
def list_results(
    job_id: int | None = Query(default=None),
    shortlisted_only: bool = Query(default=False),
    db: Session = Depends(get_db),
) -> list[MatchOut]:
    query = db.query(MatchResult)
    if job_id is not None:
        query = query.filter(MatchResult.job_id == job_id)
    if shortlisted_only:
        query = query.filter(MatchResult.shortlisted == 1)

    matches = query.order_by(MatchResult.score.desc()).all()
    return [_match_out(m) for m in matches]


@router.get("/shortlist/{job_id}", response_model=list[MatchOut])
def shortlist(job_id: int, db: Session = Depends(get_db)) -> list[MatchOut]:
    job = db.get(JobDescription, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    matches = (
        db.query(MatchResult)
        .filter(MatchResult.job_id == job_id, MatchResult.shortlisted == 1)
        .order_by(MatchResult.score.desc())
        .all()
    )
    return [_match_out(m) for m in matches]
