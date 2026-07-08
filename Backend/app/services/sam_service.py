# Repo path: Backend/app/services/sam_service.py  (NEW FILE)
"""
MobileSAM (ai_experiments) integration service.

Wraps the MobileSAM model so the frontend can request an automatic
segmentation mask by clicking a single point on the uploaded image.

The model is loaded lazily and kept as a process-wide singleton so the
heavy encoder only runs once per image (mirrors the pattern in
ai_experiments/mobilesam_test/test_mobilesam.py, but without the
interactive matplotlib prompt).

The returned mask follows the SAME contract as the hand-drawn annotation
mask used everywhere else in the studio:
  - White (#FFFFFF) = editable region (the segmented object)
  - Black (#000000) = protected / untouched region
This lets the existing generation_service.apply the effect inside the
SAM-produced mask with zero contract changes.
"""
import logging
import threading
from io import BytesIO
from pathlib import Path

import numpy as np
import torch
from PIL import Image

logger = logging.getLogger(__name__)

# --- Model configuration (mirrors ai_experiments/mobilesam_test) ---
_MODEL_TYPE = "vit_t"
_CHECKPOINT = "Backend/ai_experiments/mobilesam_test/MobileSAM/weights/mobile_sam.pt"

# Process-wide singleton state, guarded by a lock for lazy init.
_lock = threading.Lock()
_predictor = None
_loaded_image_id = None


def _get_device() -> str:
    return "cuda" if torch.cuda.is_available() else "cpu"


def _load_model():
    """Lazily build and cache the MobileSAM predictor (singleton)."""
    global _predictor
    if _predictor is not None:
        return _predictor

    from mobile_sam import sam_model_registry, SamPredictor

    device = _get_device()
    logger.info("Loading MobileSAM model on device=%s", device)
    checkpoint_path = Path(_CHECKPOINT)
    if not checkpoint_path.exists():
        raise FileNotFoundError(
            f"MobileSAM checkpoint not found at {checkpoint_path}. "
            "Run the download step in ai_experiments/mobilesam_test first."
        )
    model = sam_model_registry[_MODEL_TYPE](checkpoint=str(checkpoint_path))
    model.to(device=device)
    model.eval()
    _predictor = SamPredictor(model)
    logger.info("MobileSAM model loaded")
    return _predictor


def _ensure_image_encoded(predictor, image_id: str, source_path: Path):
    """Run the (expensive) image encoder once per image."""
    global _loaded_image_id
    if _loaded_image_id == image_id:
        return
    image = np.array(Image.open(source_path).convert("RGB"))
    predictor.set_image(image)
    _loaded_image_id = image_id


def segment_from_point(
    source_path: Path,
    image_id: str,
    point_x: int,
    point_y: int,
) -> bytes:
    """
    Run MobileSAM for a single clicked point and return a black/white PNG
    mask (white = segmented region) as raw bytes.

    point_x / point_y are in IMAGE pixel coordinates (origin top-left),
    matching the coordinates the frontend records via Konva's
    getRelativePointerPosition().
    """
    with _lock:
        predictor = _load_model()
        _ensure_image_encoded(predictor, image_id, source_path)

        input_point = np.array([[float(point_x), float(point_y)]])
        input_label = np.array([1])  # 1 = point is inside the target region

        masks, scores, _ = predictor.predict(
            point_coords=input_point,
            point_labels=input_label,
            multimask_output=True,  # returns 3 candidates, ranked by score
        )

    best_mask = masks[int(np.argmax(scores))]

    # Convert boolean mask -> black/white PNG (white = editable region).
    mask_uint8 = (best_mask.astype(np.uint8)) * 255
    mask_img = Image.fromarray(mask_uint8, mode="L")

    buf = BytesIO()
    mask_img.save(buf, format="PNG")
    return buf.getvalue()