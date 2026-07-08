# Repo path: Backend/tests/test_sam.py (NEW FILE)
"""
Tests the /api/v1/sam/segment contract and the box-clipping guarantee.
Mocks app.ml.sam.predictor.predict_mask so these tests don't require the
actual MobileSAM checkpoint or torch inference at test time.
"""
import base64
import numpy as np
import pytest
from unittest.mock import patch

from fastapi.testclient import TestClient
import io
import os
from PIL import Image as PILImage

os.environ.setdefault("UPLOAD_DIR", "storage")
from app.main import app  # noqa: E402

client = TestClient(app)


@pytest.fixture
def uploaded_image_id():
    """Upload a test image and return its ID."""
    img = PILImage.new("RGB", (100, 100), color=(200, 150, 100))
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    resp = client.post(
        "/api/v1/images/upload",
        files={"file": ("test.png", buf.getvalue(), "image/png")},
    )
    assert resp.status_code == 201
    return resp.json()["image_id"]


@pytest.fixture
def uploaded_image_size():
    """Return the size of test images (width, height)."""
    return (100, 100)


def test_segment_rejects_invalid_box(uploaded_image_id):
    resp = client.post(
        "/api/v1/sam/segment",
        json={"image_id": uploaded_image_id, "box": [50, 50, 10, 10]},  # x1<x0
    )
    assert resp.status_code == 400


def test_segment_returns_404_for_missing_image():
    resp = client.post(
        "/api/v1/sam/segment",
        json={"image_id": "does-not-exist", "box": [0, 0, 10, 10]},
    )
    assert resp.status_code == 404


def test_segment_mask_never_exceeds_box(uploaded_image_id, uploaded_image_size):
    """
    Core regression test for the 'mask only the selected area' requirement:
    even if the mocked SAM prediction returns a mask that's TRUE everywhere
    (i.e. the whole image), the endpoint must clip it down to the box.
    """
    width, height = uploaded_image_size
    fake_full_image_mask = np.ones((height, width), dtype=bool)  # worst case: SAM says "everything"

    box = [width // 4, height // 4, width // 2, height // 2]

    with patch("app.services.sam_service.predict_mask", return_value=fake_full_image_mask):
        resp = client.post(
            "/api/v1/sam/segment",
            json={"image_id": uploaded_image_id, "box": box},
        )

    assert resp.status_code == 200
    mask_data_url = resp.json()["mask_data"]

    header, b64data = mask_data_url.split(",", 1)
    mask_img = PILImage.open(io.BytesIO(base64.b64decode(b64data))).convert("L")
    mask_arr = np.array(mask_img)

    # Every white pixel must be inside the box.
    white_ys, white_xs = np.where(mask_arr > 128)
    if len(white_xs):
        assert white_xs.min() >= box[0]
        assert white_xs.max() <= box[2]
        assert white_ys.min() >= box[1]
        assert white_ys.max() <= box[3]

    # And there must be SOME white pixels (the box interior), proving the
    # clip didn't zero out everything either.
    assert mask_arr.max() > 128