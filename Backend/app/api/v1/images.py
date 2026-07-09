# Repo path: Backend/app/api/v1/images.py  (NEW FILE)
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from app.core.dependencies import get_db
from app.schemas.image import ImageUploadResponse
from app.services import image_service

router = APIRouter(prefix="/images", tags=["images"])


@router.post(
    "/upload",
    response_model=ImageUploadResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Upload a cookie/biscuit image (KPI 2)",
)
async def upload_image(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    try:
        record = await image_service.process_upload(db, file)
    except image_service.UnsupportedFileTypeError as exc:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE, detail=str(exc)
        )
    except image_service.FileTooLargeError as exc:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, detail=str(exc)
        )

    return ImageUploadResponse(
        image_id=record.id,
        original_filename=record.original_filename,
        content_type=record.content_type,
        size_bytes=record.size_bytes,
        created_at=record.created_at,
    )