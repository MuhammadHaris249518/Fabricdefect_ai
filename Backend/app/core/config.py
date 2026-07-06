<<<<<<< Updated upstream
=======
# Repo path: Backend/app/core/config.py  (UPDATED — add Roboflow section)
from functools import lru_cache
from typing import List

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    APP_NAME: str = "Crumb Studio AI Backend"

    DATABASE_URL: str = "sqlite:///./crumb_studio.db"

    # Image upload (KPI 2)
    UPLOAD_DIR: str = "storage/uploads"
    MAX_UPLOAD_SIZE_MB: int = 10
    ALLOWED_IMAGE_CONTENT_TYPES: List[str] = ["image/jpeg", "image/png"]

    # Annotation / mask storage (KPI 5)
    MASK_DIR: str = "storage/masks"
    MAX_MASK_SIZE_MB: int = 15

    # Roboflow dataset sync (KPI 5/6) — best-effort, never blocks the UI.
    # Leave these blank in local/dev .env to run with Roboflow sync disabled;
    # the annotation flow works fully without them.
    ROBOFLOW_API_KEY: str = ""
    ROBOFLOW_WORKSPACE: str = ""
    ROBOFLOW_PROJECT: str = ""
    ROBOFLOW_UPLOAD_TIMEOUT: int = 15  # seconds

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


@lru_cache
def get_settings() -> Settings:
    return Settings()
>>>>>>> Stashed changes
