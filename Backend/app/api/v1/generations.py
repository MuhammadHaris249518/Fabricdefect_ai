# Repo path: Backend/app/api/v1/generations.py
"""
Generation endpoint (FR-06, FR-08, FR-13, FR-14 / KPI 6, 9).

Accepts {image_id, mask_data, prompt}, persists the mask and a
Generation record for traceability, then calls the AI generation model.

Until Workstream B delivers the real fine-tuned model, generate_defect()
returns a stub response that matches the agreed contract shape — so the
frontend can be fully integrated and tested end-to-end. When the real
model is ready, swap the logic in generate_defect() for a call to the
served model endpoint; no frontend or contract changes are needed.
"""
import base64
import binascii
import shutil
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.dependencies import get_db
from app.core.storage import get_mask_storage
from app.db import repository
from app.schemas.generation import GenerationRequest, GenerationResponse

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


def generate_defect(source_path: Path, generation_id: str, prompt: str) -> Path:
    """
    Stub for Workstream B's masked-generation model.

    Currently copies the original image as the "generated" result so the
    full request/response contract can be exercised end-to-end. Replace
    this body with a call to the served model — the signature and return
    value stay the same.
    """
    result_dir = Path("storage/results")
    result_dir.mkdir(parents=True, exist_ok=True)
    result_path = result_dir / f"result_{generation_id}{source_path.suffix}"
    shutil.copy2(str(source_path), str(result_path))
    return result_path


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
        result_path = generate_defect(source_path, generation.id, req.prompt)
    except Exception as exc:  # noqa: BLE001 - surface any model failure as a clean 500
        repository.update_generation_record(
            db, generation, status="failed", error_message=str(exc)
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Generation failed. Your image, mask, and prompt are unchanged — please retry.",
        ) from exc

    generation = repository.update_generation_record(
        db, generation, status="complete", result_path=str(result_path)
    )

    return GenerationResponse(
        id=generation.id,
        image_id=generation.image_id,
        prompt=generation.prompt,
        status=generation.status,
        result_url=f"/storage/results/{result_path.name}",
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

    return GenerationResponse(
        id=generation.id,
        image_id=generation.image_id,
        prompt=generation.prompt,
        status=generation.status,
        result_url=result_url,
        error_message=generation.error_message,
        created_at=generation.created_at,
        updated_at=generation.updated_at,
    )