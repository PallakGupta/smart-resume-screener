"""Resume upload and CRUD endpoints."""

from __future__ import annotations

import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, File, HTTPException, Response, UploadFile
from sqlalchemy.orm import Session

from app.config import get_settings
from app.database import get_db
from app.models import Resume
from app.schemas import ResumeDetail, ResumeOut
from app.services.extractor import dumps_list, extract_structured, loads_list
from app.services.parser import SUPPORTED_EXTENSIONS, extract_text_from_file

router = APIRouter(prefix="/resumes", tags=["resumes"])


def _to_out(resume: Resume, *, detail: bool = False) -> ResumeOut | ResumeDetail:
    data = {
        "id": resume.id,
        "original_filename": resume.original_filename,
        "candidate_name": resume.candidate_name,
        "email": resume.email,
        "phone": resume.phone,
        "skills": loads_list(resume.skills),
        "experience": loads_list(resume.experience),
        "education": loads_list(resume.education),
        "summary": resume.summary,
        "created_at": resume.created_at,
    }
    if detail:
        return ResumeDetail(**data, raw_text=resume.raw_text)
    return ResumeOut(**data)


@router.post("", response_model=ResumeOut, status_code=201)
async def upload_resume(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
) -> ResumeOut:
    if not file.filename:
        raise HTTPException(status_code=400, detail="Filename is required")

    suffix = Path(file.filename).suffix.lower()
    if suffix not in SUPPORTED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type. Allowed: {sorted(SUPPORTED_EXTENSIONS)}",
        )

    settings = get_settings()
    settings.upload_dir.mkdir(parents=True, exist_ok=True)
    stored_name = f"{uuid.uuid4().hex}{suffix}"
    dest = settings.upload_dir / stored_name

    content = await file.read()
    if not content:
        raise HTTPException(status_code=400, detail="Empty file")
    dest.write_bytes(content)

    try:
        raw_text = extract_text_from_file(dest)
    except ValueError as exc:
        dest.unlink(missing_ok=True)
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    structured = extract_structured(raw_text)
    resume = Resume(
        filename=stored_name,
        original_filename=file.filename,
        raw_text=raw_text,
        candidate_name=structured.get("candidate_name"),
        email=structured.get("email"),
        phone=structured.get("phone"),
        skills=dumps_list(structured.get("skills") or []),
        experience=dumps_list(structured.get("experience") or []),
        education=dumps_list(structured.get("education") or []),
        summary=structured.get("summary"),
    )
    db.add(resume)
    db.commit()
    db.refresh(resume)
    return _to_out(resume)  # type: ignore[return-value]


@router.get("", response_model=list[ResumeOut])
def list_resumes(db: Session = Depends(get_db)) -> list[ResumeOut]:
    resumes = db.query(Resume).order_by(Resume.created_at.desc()).all()
    return [_to_out(r) for r in resumes]  # type: ignore[misc]


@router.get("/{resume_id}", response_model=ResumeDetail)
def get_resume(resume_id: int, db: Session = Depends(get_db)) -> ResumeDetail:
    resume = db.get(Resume, resume_id)
    if not resume:
        raise HTTPException(status_code=404, detail="Resume not found")
    return _to_out(resume, detail=True)  # type: ignore[return-value]


@router.delete("/{resume_id}", status_code=204)
def delete_resume(resume_id: int, db: Session = Depends(get_db)) -> Response:
    resume = db.get(Resume, resume_id)
    if not resume:
        raise HTTPException(status_code=404, detail="Resume not found")

    settings = get_settings()
    path = settings.upload_dir / resume.filename
    path.unlink(missing_ok=True)

    db.delete(resume)
    db.commit()
    return Response(status_code=204)
