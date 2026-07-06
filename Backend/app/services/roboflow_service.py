# Repo path: Backend/app/services/roboflow_service.py  (NEW FILE)
"""
Thin, best-effort wrapper around Roboflow's Upload API.

Roboflow does not offer an embeddable annotation *widget* — the interactive
brush/polygon UI end users touch is our own AnnotationCanvas component
(frontend). This module's only job is to push the source image into the
team's Roboflow project so Team A/B get dataset versioning "for free."

IMPORTANT: Roboflow's upload endpoint/params have changed over the product's
history. Verify this against the current docs before relying on it in
production: https://docs.roboflow.com/api-reference/images/upload-an-image
This is intentionally isolated behind is_configured()/upload_image() so it
can be swapped without touching any calling code.
"""
import base64

import requests

from app.core.config import get_settings

settings = get_settings()

UPLOAD_URL = "https://api.roboflow.com/dataset/{project}/upload"


class RoboflowNotConfiguredError(Exception):
    pass


class RoboflowSyncError(Exception):
    pass


def is_configured() -> bool:
    return bool(
        settings.ROBOFLOW_API_KEY
        and settings.ROBOFLOW_WORKSPACE
        and settings.ROBOFLOW_PROJECT
    )


def upload_image(image_bytes: bytes, filename: str) -> str:
    """Uploads the original (unannotated) image to the configured Roboflow
    project. Returns the Roboflow-assigned image id.

    Raises RoboflowNotConfiguredError / RoboflowSyncError on failure — both
    are caught by the caller (annotation_service) and never surfaced to the
    end user as a blocking error.
    """
    if not is_configured():
        raise RoboflowNotConfiguredError("Roboflow credentials are not configured.")

    url = UPLOAD_URL.format(project=settings.ROBOFLOW_PROJECT)
    params = {"api_key": settings.ROBOFLOW_API_KEY, "name": filename}
    encoded = base64.b64encode(image_bytes).decode("utf-8")

    resp = requests.post(
        url,
        params=params,
        data=encoded,
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        timeout=settings.ROBOFLOW_UPLOAD_TIMEOUT,
    )

    if resp.status_code >= 400:
        raise RoboflowSyncError(f"Roboflow upload failed ({resp.status_code}): {resp.text[:200]}")

    body = resp.json()
    image_id = body.get("id") or (body.get("image") or {}).get("id")
    if not image_id:
        raise RoboflowSyncError("Roboflow upload succeeded but no image id was returned.")
    return image_id