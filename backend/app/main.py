"""Smart Resume Screener — FastAPI application entrypoint."""

from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.config import get_settings
from app.database import Base, engine
from app.routers import jobs, resumes, screening
from app.schemas import HealthOut
from app.services.llm import llm_available

settings = get_settings()
settings.data_dir.mkdir(parents=True, exist_ok=True)
settings.upload_dir.mkdir(parents=True, exist_ok=True)

Base.metadata.create_all(bind=engine)

app = FastAPI(
    title=settings.app_name,
    description=(
        "Parse PDF/text resumes, extract structured candidate data, "
        "and score fit against job descriptions with an LLM."
    ),
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(resumes.router, prefix=settings.api_prefix)
app.include_router(jobs.router, prefix=settings.api_prefix)
app.include_router(screening.router, prefix=settings.api_prefix)

FRONTEND_DIR = Path(__file__).resolve().parents[2] / "frontend"


@app.get("/api/health", response_model=HealthOut, tags=["health"])
def health() -> HealthOut:
    return HealthOut(
        status="ok",
        llm_configured=llm_available(),
        model=settings.openai_model if llm_available() else "heuristic-fallback",
    )


if FRONTEND_DIR.exists():
    app.mount("/assets", StaticFiles(directory=FRONTEND_DIR / "assets"), name="assets")

    @app.get("/")
    def serve_dashboard() -> FileResponse:
        return FileResponse(FRONTEND_DIR / "index.html")
