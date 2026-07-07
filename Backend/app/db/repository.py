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
