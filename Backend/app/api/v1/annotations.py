# Repo path: Backend/app/api/v1/annotations.py  (NEW FILE)
"""
KPI 5 endpoints: persist the mask produced by the in-app annotation canvas,
and report its Roboflow dataset-sync status.
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.dependencies import get_db
from app.db import repository
from app.schemas.annotation import AnnotationResponse, AnnotationSaveRequest
from app.services import annotation_service

router = APIRouter(prefix="/images", tags=["annotations"])


@router.post(
    "/{image_id}/annotation",
    response_model=AnnotationResponse,
    summary="Save the current annotation mask for an image (KPI 5)",
)
async def save_annotation(
    image_id: str,
    req: AnnotationSaveRequest,
    db: Session = Depends(get_db),
):
    image = repository.get_image_by_id(db, image_id)
    if not image:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Image '{image_id}' not found.")

    try:
        record = annotation_service.save_mask(db, image=image, mask_data_url=req.mask_data_url)
    except annotation_service.InvalidMaskError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc))

    return AnnotationResponse(
        image_id=image_id,
        mask_url=f"/storage/masks/{image_id}.png",
        mask_format=record.mask_format,
        roboflow_status=record.roboflow_status,
        roboflow_image_id=record.roboflow_image_id,
        updated_at=record.updated_at,
    )


@router.get(
    "/{image_id}/annotation",
    response_model=AnnotationResponse,
    summary="Get the saved annotation mask status for an image",
)
async def get_annotation(image_id: str, db: Session = Depends(get_db)):
    record = repository.get_annotation_by_image_id(db, image_id)
    if not record:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No annotation saved for this image yet.")

    return AnnotationResponse(
        image_id=image_id,
        mask_url=f"/storage/masks/{image_id}.png",
        mask_format=record.mask_format,
        roboflow_status=record.roboflow_status,
        roboflow_image_id=record.roboflow_image_id,
        updated_at=record.updated_at,
    )