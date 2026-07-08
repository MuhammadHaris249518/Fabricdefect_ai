# Repo path: Backend/app/api/v1/sam.py  (NEW FILE)
"""
MobileSAM segmentation endpoint (connects the ai_experiments MobileSAM
model to the frontend studio).

Flow:
  1. Frontend uploads an image (existing /images/upload) -> gets image_id.
  2. User clicks a point on the region they want in the annotation panel.
  3. Frontend calls POST /api/v1/sam/segment with {image_id, point_x, point_y}.
  4. This endpoint runs MobileSAM for that point and returns a black/white
     PNG mask (white = editable region) as a data URL.
  5. Frontend feeds that mask into the existing mask contract, so the
     existing Generate pipeline works unchanged.
"""
import base64
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.core.dependencies import get_db
from app.db import repository
from app.services.sam_service import segment_from_point

router = APIRouter(prefix="/sam", tags=["sam"])


class SegmentRequest(BaseModel):
    image_id: str = Field(..., description="ID of an already-uploaded image")
    point_x: int = Field(..., ge=0, description="Clicked point X in image pixels")
    point_y: int = Field(..., ge=0, description="Clicked point Y in image pixels")


class SegmentResponse(BaseModel):
    mask_data: str = Field(..., description="data:image/png;base64,... mask (white=editable)")


@router.post(
    "/segment",
    response_model=SegmentResponse,
    status_code=status.HTTP_200_OK,
    summary="Run MobileSAM segmentation for a clicked point",
)
async def segment(req: SegmentRequest, db: Session = Depends(get_db)):
    # 1. Verify the source image exists and is on disk.
    image = repository.get_image_by_id(db, req.image_id)
    if not image:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Image with id '{req.image_id}' not found.",
        )

    source_path = Path(image.storage_path)
    if not source_path.exists():
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Source image file not found on disk.",
        )

    # 2. Run MobileSAM for the clicked point.
    try:
        mask_bytes = segment_from_point(
            source_path, req.image_id, req.point_x, req.point_y
        )
    except FileNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        )
    except Exception as exc:  # noqa: BLE001 - surface model failure as a clean 500
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"MobileSAM segmentation failed: {exc}",
        )

    # 3. Return the mask as a data URL (same shape the frontend already uses).
    encoded = base64.b64encode(mask_bytes).decode("ascii")
    return SegmentResponse(mask_data=f"data:image/png;base64,{encoded}")