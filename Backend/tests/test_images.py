# Repo path: Backend/tests/test_images.py  (NEW FILE)
import io
import os
import tempfile
from pathlib import Path

from fastapi.testclient import TestClient
from PIL import Image as PILImage

# Point the app at a throwaway upload dir + sqlite file before importing it
os.environ.setdefault("UPLOAD_DIR", tempfile.mkdtemp())
os.environ.setdefault("DATABASE_URL", "sqlite:///./test_crumb_studio.db")

# Remove any stale test database so create_all() builds the schema fresh
_db_path = Path("test_crumb_studio.db")
if _db_path.exists():
    _db_path.unlink()
_db_path = Path("test_crumb_studio.db-wal")  # WAL journal
if _db_path.exists():
    _db_path.unlink()
_db_path = Path("test_crumb_studio.db-shm")  # Shared memory
if _db_path.exists():
    _db_path.unlink()

from app.main import app  # noqa: E402

client = TestClient(app)


def make_image_bytes(fmt="PNG"):
    img = PILImage.new("RGB", (64, 64), color=(200, 150, 100))
    buf = io.BytesIO()
    img.save(buf, format=fmt)
    return buf.getvalue()


def test_upload_valid_png():
    data = make_image_bytes("PNG")
    resp = client.post(
        "/api/v1/images/upload",
        files={"file": ("cookie.png", data, "image/png")},
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["image_id"]
    assert body["content_type"] == "image/png"
    assert body["size_bytes"] == len(data)


def test_upload_valid_jpg():
    data = make_image_bytes("JPEG")
    resp = client.post(
        "/api/v1/images/upload",
        files={"file": ("cookie.jpg", data, "image/jpeg")},
    )
    assert resp.status_code == 201
    assert resp.json()["content_type"] == "image/jpeg"


def test_upload_rejects_wrong_type():
    resp = client.post(
        "/api/v1/images/upload",
        files={"file": ("notes.txt", b"hello world", "text/plain")},
    )
    assert resp.status_code == 415


def test_upload_rejects_oversized_file():
    max_bytes = 10 * 1024 * 1024
    data = b"0" * (max_bytes + 1024)
    resp = client.post(
        "/api/v1/images/upload",
        files={"file": ("big.png", data, "image/png")},
    )
    assert resp.status_code == 413


def test_upload_rejects_empty_file():
    resp = client.post(
        "/api/v1/images/upload",
        files={"file": ("empty.png", b"", "image/png")},
    )
    assert resp.status_code == 415


def test_upload_returns_stable_id_usable_later():
    data = make_image_bytes("PNG")
    resp = client.post(
        "/api/v1/images/upload",
        files={"file": ("cookie.png", data, "image/png")},
    )
    image_id = resp.json()["image_id"]
    # A stable id should look like a uuid4 string, not an incrementing int
    # or anything request-specific.
    assert len(image_id) == 36
    assert image_id.count("-") == 4