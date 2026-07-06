# Repo path: Backend/app/services/annotation_service.py  (NEW FILE)
import base64
import re
from pathlib import Path

from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.db import repository
from app.db.models import Annotation, Image
from app.services import roboflow_service

settings = get_settings()

DATA_URL_RE = re.compile(r"^data:image/png;base64,(.+)$")


class InvalidMaskError(Exception):
    """Raised when the incoming mask isn't a decodable PNG data URL."""


def _mask_dir() -> Path:
    d = Path(settings.MASK_DIR)
    d.mkdir(parents=True, exist_ok=True)
    return d


def save_mask(db: Session, *, image: Image, mask_data_url: str) -> Annotation:
    match = DATA_URL_RE.match(mask_data_url or "")
    if not match:
        raise InvalidMaskError("mask_data_url must be a base64-encoded PNG data URL.")

    try:
        mask_bytes = base64.b64decode(match.group(1))
    except Exception as exc:  # noqa: BLE001
        raise InvalidMaskError(f"Could not decode mask image: {exc}")

    if len(mask_bytes) == 0:
        raise InvalidMaskError("Mask image is empty.")

    max_bytes = settings.MAX_MASK_SIZE_MB * 1024 * 1024
    if len(mask_bytes) > max_bytes:
        raise InvalidMaskError(f"Mask exceeds the {settings.MAX_MASK_SIZE_MB}MB size limit.")

    mask_path = _mask_dir() / f"{image.id}.png"
    with open(mask_path, "wb") as f:
        f.write(mask_bytes)

    # Best-effort Roboflow dataset sync. Failure here never blocks the
    # annotation flow — the locally saved mask is always the source of truth
    # for generation (KPI 9).
    roboflow_status = "disabled"
    roboflow_image_id = None
    roboflow_error = None

    if roboflow_service.is_configured():
        try:
            source_bytes = Path(image.storage_path).read_bytes()
            roboflow_image_id = roboflow_service.upload_image(source_bytes, image.original_filename)
            roboflow_status = "synced"
        except Exception as exc:  # noqa: BLE001
            roboflow_status = "failed"
            roboflow_error = str(exc)[:500]

    return repository.upsert_annotation(
        db,
        image_id=image.id,
        mask_path=str(mask_path),
        roboflow_status=roboflow_status,
        roboflow_image_id=roboflow_image_id,
        roboflow_error=roboflow_error,
    )