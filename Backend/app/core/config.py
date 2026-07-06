# Repo path: Backend/app/core/config.py  (UPDATED)
from functools import lru_cache
from typing import List

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    APP_NAME: str = "Crumb Studio AI Backend"

    # Database.
    # Default is local SQLite so the app runs with zero setup.
    # For Supabase Postgres, set DATABASE_URL in Backend/.env, e.g.:
    #   postgresql+psycopg2://postgres:<password>@db.<project-ref>.supabase.co:5432/postgres
    # See Backend/.env.example for the exact format and where to get it.
    DATABASE_URL: str = "sqlite:///./crumb_studio.db"

    # Image upload (KPI 2)
    UPLOAD_DIR: str = "storage/uploads"
    MAX_UPLOAD_SIZE_MB: int = 10
    ALLOWED_IMAGE_CONTENT_TYPES: List[str] = ["image/jpeg", "image/png"]

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


@lru_cache
def get_settings() -> Settings:
    return Settings()