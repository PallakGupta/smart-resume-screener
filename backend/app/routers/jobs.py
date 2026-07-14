"""Job description CRUD endpoints."""

from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import JobDescription
from app.schemas import JobCreate, JobOut
from app.services.extractor import dumps_list, loads_list
from app.services.matcher import extract_job_skills

router = APIRouter(prefix="/jobs", tags=["jobs"])


def _to_out(job: JobDescription) -> JobOut:
    return JobOut(
        id=job.id,
        title=job.title,
        company=job.company,
        description=job.description,
        required_skills=loads_list(job.required_skills),
        created_at=job.created_at,
    )


@router.post("", response_model=JobOut, status_code=201)
def create_job(payload: JobCreate, db: Session = Depends(get_db)) -> JobOut:
    skills = payload.required_skills
    if not skills:
        skills = extract_job_skills(payload.title, payload.description)

    job = JobDescription(
        title=payload.title.strip(),
        company=(payload.company.strip() if payload.company else None),
        description=payload.description.strip(),
        required_skills=dumps_list(skills),
    )
    db.add(job)
    db.commit()
    db.refresh(job)
    return _to_out(job)


@router.get("", response_model=list[JobOut])
def list_jobs(db: Session = Depends(get_db)) -> list[JobOut]:
    jobs = db.query(JobDescription).order_by(JobDescription.created_at.desc()).all()
    return [_to_out(j) for j in jobs]


@router.get("/{job_id}", response_model=JobOut)
def get_job(job_id: int, db: Session = Depends(get_db)) -> JobOut:
    job = db.get(JobDescription, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return _to_out(job)


@router.delete("/{job_id}", status_code=204)
def delete_job(job_id: int, db: Session = Depends(get_db)) -> Response:
    job = db.get(JobDescription, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    db.delete(job)
    db.commit()
    return Response(status_code=204)
