# Repo path: Backend/app/core/storage.py  (NEW FILE)
"""
Filesystem-backed storage for uploaded images.

This is the "object storage or equivalent" referenced in KPI 2. It's kept
behind a small class with save()/path_for() so it can be swapped for an
S3/GCS-backed implementation later without touching any calling code.
"""
import uuid
from pathlib import Path
from typing import Tuple

from app.core.config import get_settings

settings = get_settings()


class LocalImageStorage:
    def __init__(self, base_dir: str | None = None):
        self.base_dir = Path(base_dir or settings.UPLOAD_DIR)
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def save(self, file_bytes: bytes, extension: str) -> Tuple[str, str]:
        """Writes the raw bytes unmodified. Returns (image_id, stored_path)."""
        image_id = str(uuid.uuid4())
        stored_path = self.base_dir / f"{image_id}{extension}"
        with open(stored_path, "wb") as f:
            f.write(file_bytes)
        return image_id, str(stored_path)

    def path_for(self, image_id: str, extension: str) -> str:
        return str(self.base_dir / f"{image_id}{extension}")


class LocalMaskStorage:
    """Stores annotation-derived masks (PNG, white=edit region / black=untouched)."""

    def __init__(self, base_dir: str | None = None):
        self.base_dir = Path(base_dir or "storage/masks")
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def save(self, file_bytes: bytes, generation_id: str) -> str:
        stored_path = self.base_dir / f"{generation_id}.png"
        with open(stored_path, "wb") as f:
            f.write(file_bytes)
        return str(stored_path)


def get_storage() -> LocalImageStorage:
    return LocalImageStorage()


def get_mask_storage() -> LocalMaskStorage:
    return LocalMaskStorage()