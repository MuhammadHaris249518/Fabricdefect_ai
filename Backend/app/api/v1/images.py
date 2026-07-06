import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.dependencies import get_db
from app.db import repository

router = APIRouter(prefix="/images", tags=["images"])
settings = get_settings()


@router.post("/upload")
async def upload_image(file: UploadFile = File(...), db: Session = Depends(get_db)):
    if file.content_type not in settings.ALLOWED_IMAGE_CONTENT_TYPES:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail=f"Unsupported content type: {file.content_type}",
        )

    contents = await file.read()
    max_bytes = settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024
    if len(contents) > max_bytes:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File is too large. Maximum size is {settings.MAX_UPLOAD_SIZE_MB} MB.",
        )

    Path(settings.UPLOAD_DIR).mkdir(parents=True, exist_ok=True)
    image_id = str(uuid.uuid4())
    extension = Path(file.filename).suffix
    filename = f"{image_id}{extension}"
    storage_path = Path(settings.UPLOAD_DIR) / filename

    with open(storage_path, "wb") as out_file:
        out_file.write(contents)

    record = repository.create_image_record(
        db,
        image_id=image_id,
        filename=file.filename,
        content_type=file.content_type,
        size_bytes=len(contents),
        storage_path=str(storage_path),
    )

    return {
        "image_id": record.id,
        "original_filename": record.original_filename,
        "content_type": record.content_type,
        "size_bytes": record.size_bytes,
        "storage_path": record.storage_path,
        "created_at": record.created_at,
    }
