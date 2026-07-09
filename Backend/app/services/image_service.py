# Repo path: Backend/app/services/image_service.py  (NEW FILE)
from fastapi import UploadFile
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.storage import get_storage
from app.db import repository
from app.db.models import Image

settings = get_settings()

ALLOWED_CONTENT_TYPES = {
    "image/jpeg": ".jpg",
    "image/png": ".png",
}


class UnsupportedFileTypeError(Exception):
    """Raised for wrong content type or an empty file."""


class FileTooLargeError(Exception):
    """Raised when the upload exceeds MAX_UPLOAD_SIZE_MB."""


async def process_upload(db: Session, file: UploadFile) -> Image:
    if file.content_type not in ALLOWED_CONTENT_TYPES:
        raise UnsupportedFileTypeError(
            f"Unsupported file type '{file.content_type}'. Only JPG and PNG images are accepted."
        )

    max_bytes = settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024
    file_bytes = await file.read()

    if len(file_bytes) == 0:
        raise UnsupportedFileTypeError("Uploaded file is empty.")

    if len(file_bytes) > max_bytes:
        raise FileTooLargeError(
            f"File exceeds the {settings.MAX_UPLOAD_SIZE_MB}MB size limit."
        )

    extension = ALLOWED_CONTENT_TYPES[file.content_type]
    storage = get_storage()
    image_id, storage_path = storage.save(file_bytes, extension)

    record = repository.create_image_record(
        db,
        image_id=image_id,
        filename=file.filename or f"{image_id}{extension}",
        content_type=file.content_type,
        size_bytes=len(file_bytes),
        storage_path=storage_path,
    )
    return record