# Repo path: Backend/app/services/sam_service.py (REWRITTEN)
"""
Request-level orchestration for MobileSAM-assisted mask refinement.

Contract: given an already-stored image and the user's rough selection
(a box, required; an optional disambiguation point), returns a black/white
PNG mask (white = editable region) that is GUARANTEED to be a subset of
the user's rough selection — SAM can only tighten the boundary inward, it
can never paint outside what the user selected. This is enforced by
intersecting SAM's raw output with a rasterized version of the box.
"""
import logging
from io import BytesIO
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

from app.ml.sam.predictor import predict_mask

logger = logging.getLogger(__name__)


def _rasterize_box(box: list[int], width: int, height: int) -> np.ndarray:
    """Boolean mask, True inside the box, used as the hard clip ceiling."""
    img = Image.new("L", (width, height), 0)
    draw = ImageDraw.Draw(img)
    x0, y0, x1, y1 = box
    draw.rectangle([x0, y0, x1, y1], fill=255)
    return np.array(img) > 128


def _save_debug_mask_preview(clipped_mask: np.ndarray, image_id: str) -> Path:
    """
    Writes a black/white PNG purely for visual debugging of SAM's
    segmentation quality. This is NOT the mask returned to the frontend and
    is NOT read by anything else in the codebase — generation_service.py's
    _load_mask() still expects white=editable, unchanged by this function.

    Convention here (intentionally the inverse of the real mask contract,
    because it reads more naturally for a human scanning a folder of
    results — "black marks what changed"):
      - Black (0)   = region MobileSAM selected
      - White (255) = everything else

    Saved to storage/results/mask_preview_<image_id>.png. Safe to call on
    every /sam/segment request; each call overwrites the previous preview
    for that image_id.
    """
    preview_dir = Path(__file__).resolve().parent.parent / "storage" / "results"
    preview_dir.mkdir(parents=True, exist_ok=True)

    inverted = np.where(clipped_mask, 0, 255).astype(np.uint8)
    preview_path = preview_dir / f"mask_preview_{image_id}.png"
    Image.fromarray(inverted, mode="L").save(preview_path)

    logger.info("Saved SAM debug mask preview to %s", preview_path)
    return preview_path


def segment_within_box(
    source_path: Path,
    image_id: str,
    box: list[int],
    point: tuple[int, int] | None = None,
) -> bytes:
    """
    Runs MobileSAM constrained to `box`, clips the result to the box as a
    safety net against edge bleed, and returns a black/white PNG (white =
    editable region) as raw bytes — same contract as the manual brush/
    polygon mask, so generation_service.py needs no changes.
    """
    with Image.open(source_path) as src:
        width, height = src.size

    raw_mask = predict_mask(source_path, image_id, box=box, point=point)  # bool (H, W)

    selection_ceiling = _rasterize_box(box, width, height)
    clipped_mask = raw_mask & selection_ceiling  # AND: never exceed the user's box

    _save_debug_mask_preview(clipped_mask, image_id)

    mask_uint8 = clipped_mask.astype(np.uint8) * 255
    mask_img = Image.fromarray(mask_uint8, mode="L")

    buf = BytesIO()
    mask_img.save(buf, format="PNG")
    return buf.getvalue()