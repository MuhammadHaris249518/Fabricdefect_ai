# Repo path: Backend/app/api/v1/sam.py (REWRITTEN — box-prompted contract)
"""
MobileSAM segmentation endpoint, box-prompted.

Flow:
  1. Frontend uploads an image (existing /images/upload) -> gets image_id.
  2. User drags a rough rectangle over the region they want (reusing the
     existing rectangle-drawing interaction).
  3. Frontend calls POST /api/v1/sam/segment with
     {image_id, box: [x0,y0,x1,y1], point?: {x,y}}.
  4. Backend runs MobileSAM constrained to that box, clips the result to
     the box, and returns a black/white PNG mask (white = editable region)
     as a data URL.
  5. Frontend feeds that mask into the existing mask contract unchanged.
"""
import base64
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.core.dependencies import get_db
from app.db import repository
from app.services.sam_service import segment_within_box

router = APIRouter(prefix="/sam", tags=["sam"])


class SamPoint(BaseModel):
    x: int = Field(..., ge=0)
    y: int = Field(..., ge=0)


class SegmentRequest(BaseModel):
    image_id: str = Field(..., description="ID of an already-uploaded image")
    box: list[int] = Field(
        ..., min_length=4, max_length=4,
        description="[x0, y0, x1, y1] in image pixels — the user's rough selection",
    )
    point: SamPoint | None = Field(
        default=None,
        description="Optional disambiguation point inside the box",
    )


class SegmentResponse(BaseModel):
    mask_data: str = Field(..., description="data:image/png;base64,... mask (white=editable)")


@router.post(
    "/segment",
    response_model=SegmentResponse,
    status_code=status.HTTP_200_OK,
    summary="Run box-prompted MobileSAM segmentation, clipped to the box",
)
async def segment(req: SegmentRequest, db: Session = Depends(get_db)):
    image = repository.get_image_by_id(db, req.image_id)
    if not image:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"Image with id '{req.image_id}' not found.")

    source_path = Path(image.storage_path)
    if not source_path.exists():
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, "Source image file not found on disk.")

    x0, y0, x1, y1 = req.box
    if x1 <= x0 or y1 <= y0:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "box must have x1 > x0 and y1 > y0.")

    point_tuple = (req.point.x, req.point.y) if req.point else None

    try:
        mask_bytes = segment_within_box(source_path, req.image_id, req.box, point_tuple)
    except FileNotFoundError as exc:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, str(exc))
    except Exception as exc:  # noqa: BLE001 — surface model failure as a clean 500
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, f"MobileSAM segmentation failed: {exc}")

    encoded = base64.b64encode(mask_bytes).decode("ascii")
    return SegmentResponse(mask_data=f"data:image/png;base64,{encoded}")
