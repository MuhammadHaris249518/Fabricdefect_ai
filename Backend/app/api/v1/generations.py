# Repo path: Backend/app/api/v1/generations.py
"""
Generation endpoint (FR-06, FR-08, FR-13, FR-14 / KPI 6, 9).

Accepts {image_id, mask_data, prompt}, persists the mask and a
Generation record for traceability, then calls the AI generation model
constrained to the user's mask region.

Until Workstream B delivers the real fine-tuned model, the generation
service applies a synthetic effect matched to the prompt category, but
ONLY within the white region of the mask — the rest of the image is
left untouched. When the real model is ready, swap the logic in
generation_service.generate_defect() for a call to the served model
endpoint; no frontend or contract changes are needed.
"""
import base64
import binascii
import logging
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.dependencies import get_db
from app.core.storage import get_mask_storage
from app.db import repository
from app.schemas.generation import GenerationRequest, GenerationResponse
from app.services.generation_service import generate_defect

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/generations", tags=["generations"])


def _decode_mask(mask_data: str) -> bytes:
    """Strips an optional data-URI prefix and base64-decodes the mask."""
    payload = mask_data.split(",", 1)[1] if mask_data.startswith("data:") else mask_data
    try:
        return base64.b64decode(payload, validate=True)
    except (binascii.Error, ValueError) as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="mask_data is not valid base64-encoded image data.",
        ) from exc


@router.post(
    "",
    response_model=GenerationResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Generate a synthetic defect from an image, mask, and prompt",
)
async def create_generation(
    req: GenerationRequest,
    db: Session = Depends(get_db),
):
    # 1. Verify the source image exists (FR-14: fail clearly, keep state intact)
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

    # 2. Create the session record up front (FR-13: one row per request)
    generation = repository.create_generation_record(db, image_id=req.image_id, prompt=req.prompt)

    # 3. Decode and persist the mask (FR-06)
    mask_bytes = _decode_mask(req.mask_data)
    mask_path = get_mask_storage().save(mask_bytes, generation.id)
    generation = repository.update_generation_record(
        db, generation, mask_reference=mask_path, status="processing"
    )

    # 4. Call the (stub) generation model, constrained to the masked region
    try:
        result_path = generate_defect(source_path, mask_path, generation.id, req.prompt)
    except Exception as exc:  # noqa: BLE001 - surface any model failure as a clean 500
        import traceback
        error_detail = traceback.format_exc()
        logger.error("Generation failed: %s\n%s", exc, error_detail)
        repository.update_generation_record(
            db, generation, status="failed", error_message=str(exc)
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Generation failed: {exc}",
        ) from exc

    generation = repository.update_generation_record(
        db, generation, status="complete", result_path=str(result_path)
    )

    mask_filename = Path(generation.mask_reference).name if generation.mask_reference else None

    return GenerationResponse(
        id=generation.id,
        image_id=generation.image_id,
        prompt=generation.prompt,
        status=generation.status,
        result_url=f"/storage/results/{result_path.name}",
        mask_url=f"/storage/masks/{mask_filename}" if mask_filename else None,
        error_message=generation.error_message,
        created_at=generation.created_at,
        updated_at=generation.updated_at,
    )


@router.get(
    "/{generation_id}",
    response_model=GenerationResponse,
    summary="Get the status/result of a specific generation request",
)
async def get_generation(generation_id: str, db: Session = Depends(get_db)):
    generation = repository.get_generation_by_id(db, generation_id)
    if not generation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Generation with id '{generation_id}' not found.",
        )

    result_url = None
    if generation.result_path:
        result_url = f"/storage/results/{Path(generation.result_path).name}"

    mask_url = None
    if generation.mask_reference:
        mask_url = f"/storage/masks/{Path(str(generation.mask_reference)).name}"

    return GenerationResponse(
        id=generation.id,
        image_id=generation.image_id,
        prompt=generation.prompt,
        status=generation.status,
        result_url=result_url,
        mask_url=mask_url,
        error_message=generation.error_message,
        created_at=generation.created_at,
        updated_at=generation.updated_at,
    )
