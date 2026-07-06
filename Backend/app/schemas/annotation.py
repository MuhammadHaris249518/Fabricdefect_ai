# Repo path: Backend/app/schemas/annotation.py  (NEW FILE)
from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class AnnotationSaveRequest(BaseModel):
    # e.g. "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAA..."
    mask_data_url: str


class AnnotationResponse(BaseModel):
    image_id: str
    mask_url: str
    mask_format: str
    roboflow_status: str
    roboflow_image_id: Optional[str] = None
    updated_at: datetime

    class Config:
        from_attributes = True