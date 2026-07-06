import uuid
from typing import Optional

from sqlalchemy.orm import Session

from app.db.models import Annotation, Image


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


def upsert_annotation(
    db: Session,
    *,
    image_id: str,
    mask_path: str,
    roboflow_status: str,
    roboflow_image_id: Optional[str] = None,
    roboflow_error: Optional[str] = None,
) -> Annotation:
    record = db.query(Annotation).filter(Annotation.image_id == image_id).first()
    if record is None:
        record = Annotation(id=str(uuid.uuid4()), image_id=image_id)
        db.add(record)

    record.mask_path = mask_path
    record.roboflow_status = roboflow_status
    record.roboflow_image_id = roboflow_image_id
    record.roboflow_error = roboflow_error

    db.commit()
    db.refresh(record)
    return record


def get_annotation_by_image_id(db: Session, image_id: str) -> Optional[Annotation]:
    return db.query(Annotation).filter(Annotation.image_id == image_id).first()
