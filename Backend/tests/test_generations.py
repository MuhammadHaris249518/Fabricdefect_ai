
# Repo path: Backend/tests/test_generations.py (NEW FILE)
"""Contract tests for POST /api/v1/generations — {image_id, mask_data, prompt}."""
import base64
import io
import os
import pytest
from PIL import Image as PILImage
from fastapi.testclient import TestClient

os.environ.setdefault("UPLOAD_DIR", "storage")
from app.main import app  # noqa: E402

client = TestClient(app)


def make_image_bytes(fmt="PNG"):
    img = PILImage.new("RGB", (64, 64), color=(200, 150, 100))
    buf = io.BytesIO()
    img.save(buf, format=fmt)
    return buf.getvalue()


def make_sample_mask_data_url():
    """Create a simple black-square-with-white-box PNG encoded as a data URL."""
    mask = PILImage.new("L", (64, 64), 0)
    draw_mask = PILImage.new("L", (64, 64), 0)
    from PIL import ImageDraw
    draw = ImageDraw.Draw(draw_mask)
    draw.rectangle([10, 10, 50, 50], fill=255)
    buf = io.BytesIO()
    draw_mask.save(buf, format="PNG")
    return f"data:image/png;base64,{base64.b64encode(buf.getvalue()).decode('ascii')}"


@pytest.fixture
def uploaded_image_id():
    data = make_image_bytes("PNG")
    resp = client.post(
        "/api/v1/images/upload",
        files={"file": ("cookie.png", data, "image/png")},
    )
    assert resp.status_code == 201
    return resp.json()["image_id"]


def test_generation_requires_mask_data(uploaded_image_id):
    resp = client.post(
        "/api/v1/generations",
        json={"image_id": uploaded_image_id, "prompt": "Make it burned."},
    )
    assert resp.status_code in (400, 422)


def test_generation_happy_path(uploaded_image_id):
    sample_mask_data_url = make_sample_mask_data_url()
    resp = client.post(
        "/api/v1/generations",
        json={
            "image_id": uploaded_image_id,
            "prompt": "Make the selected area appear burned.",
            "mask_data": sample_mask_data_url,
        },
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["status"] in ("complete", "processing", "pending")
    assert "id" in body