# Repo path: Backend/app/main.py  (UPDATED)
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.api.v1 import generations, images, sam
from app.core.config import get_settings
from app.db import models  # noqa: F401
from app.db.base import Base
from app.db.migrate import run_migrations
from app.db.session import engine

settings = get_settings()

for directory in [settings.UPLOAD_DIR, "storage/results", "storage/masks", "storage"]:
    Path(directory).mkdir(parents=True, exist_ok=True)

Base.metadata.create_all(bind=engine)
run_migrations()

# Surface missing MobileSAM checkpoint at startup (not on first request)
from app.ml.sam.predictor import _CHECKPOINT as SAM_CHECKPOINT_PATH  # noqa: E402

if not SAM_CHECKPOINT_PATH.exists():
    import logging
    logging.getLogger(__name__).warning(
        "MobileSAM checkpoint not found at %s — /api/v1/sam/segment will "
        "return 503 until it is downloaded. Run "
        "`python scripts/download_sam_weights.py` from Backend/.",
        SAM_CHECKPOINT_PATH,
    )

app = FastAPI(title=settings.APP_NAME)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(images.router, prefix="/api/v1")
app.include_router(generations.router, prefix="/api/v1")
app.include_router(sam.router, prefix="/api/v1")

app.mount("/storage", StaticFiles(directory=str(Path("storage").resolve())), name="storage")


@app.get("/health", tags=["health"])
def health_check():
    return {"status": "ok"}