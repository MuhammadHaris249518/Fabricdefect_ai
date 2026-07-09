# Repo path: Backend/app/ml/sam/predictor.py (NEW FILE)
"""
Thin, cached wrapper around the MobileSAM predictor. Contains ONLY model
loading and raw inference — no HTTP, no DB, no request/response shaping.
That belongs in app/services/sam_service.py.
"""
import logging
import threading
from pathlib import Path
from typing import Optional

import numpy as np
import torch
from PIL import Image

from app.core.config import get_settings

logger = logging.getLogger(__name__)

_MODEL_TYPE = "vit_t"

_settings = get_settings()
_CHECKPOINT = Path(_settings.SAM_WEIGHTS_DIR) / "mobile_sam.pt"

_lock = threading.Lock()
_predictor = None
_loaded_image_id: Optional[str] = None


def _get_device() -> str:
    return "cuda" if torch.cuda.is_available() else "cpu"


def _load_model():
    global _predictor
    if _predictor is not None:
        return _predictor

    from mobile_sam import sam_model_registry, SamPredictor

    if not _CHECKPOINT.exists():
        raise FileNotFoundError(
            f"MobileSAM checkpoint not found at {_CHECKPOINT}. "
            "Run Backend/scripts/download_sam_weights.sh first."
        )

    device = _get_device()
    logger.info("Loading MobileSAM model on device=%s", device)
    model = sam_model_registry[_MODEL_TYPE](checkpoint=str(_CHECKPOINT))
    model.to(device=device)
    model.eval()
    _predictor = SamPredictor(model)
    logger.info("MobileSAM model loaded")
    return _predictor


def _ensure_image_encoded(predictor, image_id: str, source_path: Path):
    """Run the expensive image encoder once per image, cached by image_id."""
    global _loaded_image_id
    if _loaded_image_id == image_id:
        return
    image = np.array(Image.open(source_path).convert("RGB"))
    predictor.set_image(image)
    _loaded_image_id = image_id


def predict_mask(
    source_path: Path,
    image_id: str,
    box: Optional[list[int]] = None,
    point: Optional[tuple[int, int]] = None,
) -> np.ndarray:
    """
    Runs MobileSAM constrained to `box` (and optionally refined by a single
    positive `point` inside it). At least one of box/point must be given.

    box: [x0, y0, x1, y1] in image pixel coordinates — the user's rough
         rectangle. This is the primary constraint: SAM searches for the
         best single object WITHIN this box, not across the whole image.
    point: optional (x, y) inside the box for disambiguation when the box
           contains more than one plausible object.

    Returns a boolean numpy array (H, W), True = segmented/editable region.
    Multimask_output is deliberately False here — with a box prompt, SAM's
    single best mask is reliable; requesting 3 candidates is what the old
    point-only flow needed to compensate for ambiguity a box removes.
    """
    if box is None and point is None:
        raise ValueError("predict_mask requires at least one of box or point")

    with _lock:
        predictor = _load_model()
        _ensure_image_encoded(predictor, image_id, source_path)

        point_coords = np.array([point]) if point else None
        point_labels = np.array([1]) if point else None
        box_arr = np.array(box) if box else None

        masks, scores, _ = predictor.predict(
            point_coords=point_coords,
            point_labels=point_labels,
            box=box_arr,
            multimask_output=False,
        )

    return masks[0]