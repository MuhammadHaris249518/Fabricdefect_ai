# Repo path: Backend/app/schemas/annotation.py  (NEW FILE)
from typing import Optional

from pydantic import BaseModel


class RoboflowSessionResponse(BaseModel):
    roboflow_image_id: str
    annotate_url: str


class MaskStatusResponse(BaseModel):
    ready: bool
    mask_data: Optional[str] = None  # data:image/png;base64,... once ready
    message: Optional[str] = None