# Repo path: Backend/app/core/config.py  (UPDATED)
from functools import lru_cache
from typing import List

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    APP_NAME: str = "Crumb Studio AI Backend"

    # Must be set via .env — PostgreSQL with psycopg2 driver.
    # See env.example for the expected format.
    DATABASE_URL: str = ""

    # Image upload (KPI 2)
    UPLOAD_DIR: str = "storage/uploads"
    MAX_UPLOAD_SIZE_MB: int = 10
    ALLOWED_IMAGE_CONTENT_TYPES: List[str] = ["image/jpeg", "image/png"]

    # Roboflow annotation integration (KPI 5/6).
    # Values come from Backend/.env — see Backend/env.example for where to
    # get each one. Left blank here on purpose; nothing should be hardcoded.
    ROBOFLOW_API_KEY: str = ""
    ROBOFLOW_WORKSPACE: str = ""
    ROBOFLOW_PROJECT: str = ""
    ROBOFLOW_API_BASE: str = "https://api.roboflow.com"
    ROBOFLOW_APP_BASE: str = "https://app.roboflow.com"

    # MobileSAM
    SAM_WEIGHTS_DIR: str = "app/ml/sam/weights"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


@lru_cache
def get_settings() -> Settings:
    return Settings()