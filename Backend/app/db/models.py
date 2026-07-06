# Repo path: Backend/app/db/models.py  (UPDATED — add Annotation model)
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
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))


class Annotation(Base):
    """
    One row per image: the current mask produced by the in-app annotation
    canvas (KPI 5), plus the status of the best-effort Roboflow dataset sync.

    mask_path always points at a locally stored, authoritative PNG mask —
    generation (KPI 9) reads from here, never from Roboflow directly, so a
    Roboflow outage never blocks the product.
    """
    __tablename__ = "annotations"

    id = Column(String(36), primary_key=True, index=True)
    image_id = Column(String(36), ForeignKey("images.id"), nullable=False, unique=True, index=True)
    mask_path = Column(String(500), nullable=False)
    mask_format = Column(String(20), nullable=False, default="png_binary")

    roboflow_status = Column(String(20), nullable=False, default="disabled")  # disabled|synced|failed
    roboflow_image_id = Column(String(255), nullable=True)
    roboflow_error = Column(String(500), nullable=True)

    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )