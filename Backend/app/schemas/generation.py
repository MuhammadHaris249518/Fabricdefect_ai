# Repo path: Backend/app/schemas/generation.py
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class GenerationRequest(BaseModel):
    image_id: str
    prompt: str = Field(..., min_length=1, max_length=1000)
    mask_data: str = Field(..., min_length=1)


class GenerationResponse(BaseModel):
    id: str
    image_id: str
    prompt: str
    status: str
    result_url: Optional[str] = None
    mask_url: Optional[str] = None
    error_message: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
