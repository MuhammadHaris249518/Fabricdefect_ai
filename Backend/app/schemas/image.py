# Repo path: Backend/app/schemas/image.py  (NEW FILE)
from datetime import datetime

from pydantic import BaseModel


class ImageUploadResponse(BaseModel):
    image_id: str
    original_filename: str
    content_type: str
    size_bytes: int
    created_at: datetime

    class Config:
        from_attributes = True


class ErrorResponse(BaseModel):
    detail: str