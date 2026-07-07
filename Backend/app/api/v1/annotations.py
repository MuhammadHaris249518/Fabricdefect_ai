# Repo path: Backend/app/api/v1/annotations.py  (NEW FILE)
"""
Roboflow annotation endpoints (FR-03/FR-04/FR-05/FR-06, KPI 5/6).

POST /annotations/session   -> uploads the stored image into Roboflow,
                                returns the URL where the user annotates it.
GET  /annotations/mask/{id} -> polls Roboflow for that image's finished
                                annotation and rasterizes it into the same
                                black/white PNG mask format the generation
                                endpoint already expects.
"""
import base64
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, status
from PIL import Image as PILImage, ImageDraw
from sqlalchemy.orm import Session

from app.core.dependencies import get_db
from app.core.roboflow_client import RoboflowNotConfiguredError, get_roboflow_client
from app.db import repository
from app.schemas.annotation import MaskStatusResponse, RoboflowSessionResponse

router = APIRouter(prefix="/annotations", tags=["annotations"])


@router.post(
    "/session",
    response_model=RoboflowSessionResponse,
    summary="Upload an already-stored image into Roboflow and get its annotate URL",
)
async def create_roboflow_session(image_id: str, db: Session = Depends(get_db)):
    image = repository.get_image_by_id(db, image_id)
    if not image:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"Image '{image_id}' not found.")

    try:
        client = get_roboflow_client()
    except RoboflowNotConfiguredError as exc:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, str(exc)) from exc

    # Idempotent: don't re-upload if we already sent this image to Roboflow.
    if not image.roboflow_image_id:
        source_path = Path(image.storage_path)
        if not source_path.exists():
            raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, "Source image missing on disk.")

        roboflow_image_id = client.upload_image(source_path.read_bytes(), source_path.name)
        image = repository.update_image_roboflow_id(db, image, roboflow_image_id)

    return RoboflowSessionResponse(
        roboflow_image_id=image.roboflow_image_id,
        annotate_url=client.get_annotate_url(image.roboflow_image_id),
    )


def _rasterize_mask(details: dict, width: int, height: int) -> bytes:
    """Turns Roboflow's annotation JSON into a black/white PNG mask
    (white = region to edit), matching the format generations.py expects.

    Handles bounding boxes out of the box. If your project is Instance
    Segmentation, inspect a real `details["annotation"]` payload and extend
    the polygon branch below to match Roboflow's actual key names for
    polygon point lists.
    """
    mask = PILImage.new("L", (width, height), 0)
    draw = ImageDraw.Draw(mask)
    annotation = (details or {}).get("annotation") or {}

    for box in annotation.get("boxes", []):
        cx, cy, w, h = box["x"], box["y"], box["width"], box["height"]
        x0, y0 = cx - w / 2, cy - h / 2
        x1, y1 = cx + w / 2, cy + h / 2
        draw.rectangle([x0, y0, x1, y1], fill=255)

    # TODO: once you confirm the polygon key name from a real Instance
    # Segmentation response, add e.g.:
    # for polygon in annotation.get("polygons", []):
    #     points = [(p["x"], p["y"]) for p in polygon["points"]]
    #     draw.polygon(points, fill=255)

    from io import BytesIO
    buf = BytesIO()
    mask.convert("RGB").save(buf, format="PNG")
    return buf.getvalue()


@router.get(
    "/mask/{image_id}",
    response_model=MaskStatusResponse,
    summary="Check Roboflow for a finished annotation and return it as a mask",
)
async def get_roboflow_mask(image_id: str, db: Session = Depends(get_db)):
    image = repository.get_image_by_id(db, image_id)
    if not image:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"Image '{image_id}' not found.")
    if not image.roboflow_image_id:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            "No Roboflow session exists for this image yet — call /annotations/session first.",
        )

    try:
        client = get_roboflow_client()
    except RoboflowNotConfiguredError as exc:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, str(exc)) from exc

    details = client.get_image_details(image.roboflow_image_id)
    if not client.is_annotated(details):
        return MaskStatusResponse(ready=False, message="Not annotated in Roboflow yet.")

    source_path = Path(image.storage_path)
    with PILImage.open(source_path) as src:
        width, height = src.size

    mask_bytes = _rasterize_mask(details, width, height)
    mask_b64 = base64.b64encode(mask_bytes).decode("ascii")
    return MaskStatusResponse(ready=True, mask_data=f"data:image/png;base64,{mask_b64}")