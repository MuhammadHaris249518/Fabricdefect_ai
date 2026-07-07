# Repo path: Backend/app/core/roboflow_client.py  (NEW FILE)
"""
Thin wrapper around Roboflow's REST API.

Docs referenced:
  - Upload an Image:  https://docs.roboflow.com/developer/rest-api/manage-images/upload-an-image
  - Get Image Details: https://docs.roboflow.com/api-reference/images/image-details

Roboflow does not offer an embeddable end-user annotation widget — its
Annotate tool lives inside app.roboflow.com as part of a Roboflow workspace.
So the real integration is:
  1. Upload the image into your Roboflow project (this module, upload_image).
  2. Send the user to Roboflow's own hosted annotate page for that image
     (this module, get_annotate_url) to draw the mask with Roboflow's tools.
  3. Poll Roboflow for that image's finished annotation (get_image_details)
     once the user says they're done, then rasterize it into a mask PNG
     (done in the annotations router, not here).
"""
from typing import Optional

import httpx

from app.core.config import get_settings

settings = get_settings()


class RoboflowNotConfiguredError(Exception):
    """Raised when ROBOFLOW_API_KEY / WORKSPACE / PROJECT aren't set."""


class RoboflowClient:
    def __init__(
        self,
        api_key: Optional[str] = None,
        workspace: Optional[str] = None,
        project: Optional[str] = None,
        api_base: Optional[str] = None,
        app_base: Optional[str] = None,
    ):
        self.api_key = api_key or settings.ROBOFLOW_API_KEY
        self.workspace = workspace or settings.ROBOFLOW_WORKSPACE
        self.project = project or settings.ROBOFLOW_PROJECT
        self.api_base = (api_base or settings.ROBOFLOW_API_BASE).rstrip("/")
        self.app_base = (app_base or settings.ROBOFLOW_APP_BASE).rstrip("/")

        if not (self.api_key and self.workspace and self.project):
            raise RoboflowNotConfiguredError(
                "ROBOFLOW_API_KEY, ROBOFLOW_WORKSPACE, and ROBOFLOW_PROJECT must "
                "all be set in Backend/.env — see Backend/env.example."
            )

    def upload_image(self, file_bytes: bytes, filename: str) -> str:
        """Uploads one image to the configured Roboflow project.

        Returns the Roboflow-assigned image id, used for every later call.
        """
        url = f"{self.api_base}/dataset/{self.project}/upload"
        params = {"api_key": self.api_key, "name": filename}
        files = {"file": (filename, file_bytes)}

        resp = httpx.post(url, params=params, files=files, timeout=30.0)
        resp.raise_for_status()
        data = resp.json()
        return data["id"]

    def get_annotate_url(self, roboflow_image_id: str) -> str:
        """The real, hosted Roboflow page where a human draws the mask.

        This is not embeddable via iframe in the general case — Roboflow's
        app may set X-Frame-Options/CSP that blocks framing. Open it in a
        new tab as the reliable path; the frontend also tries an iframe
        first as a bonus for workspaces that do allow it.
        """
        return f"{self.app_base}/{self.workspace}/{self.project}/annotate/{roboflow_image_id}"

    def get_image_details(self, roboflow_image_id: str) -> dict:
        """Fetches the current annotation state for one image from Roboflow.

        Response shape (per Roboflow's docs) includes an "annotation" object
        with a "boxes" array for bounding-box projects. For an
        Instance Segmentation project, Roboflow also includes polygon point
        data on each annotated object — inspect a real response from your
        project and adjust `extract_regions` in annotations.py if the key
        names differ from what's assumed there.
        """
        url = f"{self.api_base}/{self.workspace}/{self.project}/images/{roboflow_image_id}"
        params = {"api_key": self.api_key}

        resp = httpx.get(url, params=params, timeout=15.0)
        resp.raise_for_status()
        return resp.json()

    def is_annotated(self, details: dict) -> bool:
        annotation = (details or {}).get("annotation") or {}
        boxes = annotation.get("boxes") or []
        polygons = annotation.get("polygons") or []
        return bool(boxes or polygons)


def get_roboflow_client() -> RoboflowClient:
    return RoboflowClient()