"""Application configuration loaded from environment variables."""

from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "Smart Resume Screener"
    api_prefix: str = "/api"
    debug: bool = True

    # SQLite by default; override with DATABASE_URL for Postgres
    database_url: str = "sqlite:///./data/screener.db"

    # OpenAI-compatible LLM
    openai_api_key: str = ""
    openai_base_url: str = "https://api.openai.com/v1"
    openai_model: str = "gpt-4o-mini"

    # Local paths
    upload_dir: Path = Path("uploads")
    data_dir: Path = Path("data")

    # Shortlist threshold (1–10 scale)
    shortlist_min_score: float = 6.0


@lru_cache
def get_settings() -> Settings:
    return Settings()
