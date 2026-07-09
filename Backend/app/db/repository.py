from datetime import datetime, timezone
from typing import Optional

from sqlalchemy.orm import Session

from app.db.models import Generation, Image


def create_image_record(
    db: Session,
    *,
    image_id: str,
    filename: str,
    content_type: str,
    size_bytes: int,
    storage_path: str,
) -> Image:
    record = Image(
        id=image_id,
        original_filename=filename,
        content_type=content_type,
        size_bytes=size_bytes,
        storage_path=storage_path,
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    return record


def get_image_by_id(db: Session, image_id: str) -> Optional[Image]:
    return db.query(Image).filter(Image.id == image_id).first()


def update_image_roboflow_id(db: Session, image: Image, roboflow_image_id: str) -> Image:
    image.roboflow_image_id = roboflow_image_id
    db.add(image)
    db.commit()
    db.refresh(image)
    return image


def create_generation_record(
    db: Session,
    *,
    image_id: str,
    prompt: str,
) -> Generation:
    record = Generation(
        image_id=image_id,
        prompt=prompt,
        status="pending",
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    return record


def update_generation_record(
    db: Session,
    generation: Generation,
    *,
    mask_reference: Optional[str] = None,
    status: Optional[str] = None,
    result_path: Optional[str] = None,
    error_message: Optional[str] = None,
) -> Generation:
    if mask_reference is not None:
        generation.mask_reference = mask_reference
    if status is not None:
        generation.status = status
    if result_path is not None:
        generation.result_path = result_path
    if error_message is not None:
        generation.error_message = error_message
    generation.updated_at = datetime.now(timezone.utc)
    db.add(generation)
    db.commit()
    db.refresh(generation)
    return generation


def get_generation_by_id(db: Session, generation_id: str) -> Optional[Generation]:
    return db.query(Generation).filter(Generation.id == generation_id).first()
