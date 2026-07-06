# Repo path: Backend/tests/test_annotations.py  (NEW FILE)
import base64
import io
import os
import tempfile

from fastapi.testclient import TestClient
from PIL import Image as PILImage

os.environ.setdefault("UPLOAD_DIR", tempfile.mkdtemp())
os.environ.setdefault("MASK_DIR", tempfile.mkdtemp())
os.environ.setdefault("DATABASE_URL", "sqlite:///./test_crumb_studio_annotations.db")

from app.main import app  # noqa: E402

client = TestClient(app)


def _upload_test_image() -> str:
    img = PILImage.new("RGB", (64, 64), color=(200, 150, 100))
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    resp = client.post(
        "/api/v1/images/upload",
        files={"file": ("cookie.png", buf.getvalue(), "image/png")},
    )
    return resp.json()["image_id"]


def _mask_data_url() -> str:
    mask = PILImage.new("L", (64, 64), color=0)
    mask.putpixel((32, 32), 255)
    buf = io.BytesIO()
    mask.save(buf, format="PNG")
    encoded = base64.b64encode(buf.getvalue()).decode("utf-8")
    return f"data:image/png;base64,{encoded}"


def test_save_annotation_for_missing_image_returns_404():
    resp = client.post(
        "/api/v1/images/does-not-exist/annotation",
        json={"mask_data_url": _mask_data_url()},
    )
    assert resp.status_code == 404


def test_save_and_fetch_annotation():
    image_id = _upload_test_image()

    save_resp = client.post(
        f"/api/v1/images/{image_id}/annotation",
        json={"mask_data_url": _mask_data_url()},
    )
    assert save_resp.status_code == 200
    body = save_resp.json()
    assert body["image_id"] == image_id
    assert body["mask_url"] == f"/storage/masks/{image_id}.png"
    # No ROBOFLOW_* env vars set in tests -> sync is disabled, not "failed"
    assert body["roboflow_status"] == "disabled"

    get_resp = client.get(f"/api/v1/images/{image_id}/annotation")
    assert get_resp.status_code == 200
    assert get_resp.json()["image_id"] == image_id


def test_save_annotation_rejects_malformed_mask():
    image_id = _upload_test_image()
    resp = client.post(
        f"/api/v1/images/{image_id}/annotation",
        json={"mask_data_url": "not-a-data-url"},
    )
    assert resp.status_code == 422