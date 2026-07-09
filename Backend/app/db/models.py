# Repo path: Backend/app/db/models.py  (UPDATED)
import uuid
from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String

from app.db.base import Base


class Image(Base):
    __tablename__ = "images"

    id = Column(String(36), primary_key=True, index=True)
    original_filename = Column(String(255), nullable=False)
    content_type = Column(String(50), nullable=False)
    size_bytes = Column(Integer, nullable=False)
    storage_path = Column(String(500), nullable=False)
    # Set once this image has been uploaded into the Roboflow project for
    # annotation (KPI 5/6). Null until POST /annotations/session runs.
    roboflow_image_id = Column(String(64), nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))


class Generation(Base):
    __tablename__ = "generations"

    id = Column(String(36), primary_key=True, index=True, default=lambda: str(uuid.uuid4()))
    image_id = Column(String(36), ForeignKey("images.id"), nullable=False, index=True)
    prompt = Column(String(1000), nullable=False)
    mask_reference = Column(String(500), nullable=True)
    status = Column(String(20), nullable=False, default="pending")
    result_path = Column(String(500), nullable=True)
    error_message = Column(String(1000), nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )