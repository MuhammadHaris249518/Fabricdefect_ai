# Repo path: Backend/app/main.py  (UPDATED)
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.api.v1 import annotations, generations, images
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

app = FastAPI(title=settings.APP_NAME)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(images.router, prefix="/api/v1")
app.include_router(annotations.router, prefix="/api/v1")
app.include_router(generations.router, prefix="/api/v1")

app.mount("/storage", StaticFiles(directory="storage"), name="storage")


@app.get("/health", tags=["health"])
def health_check():
    return {"status": "ok"}