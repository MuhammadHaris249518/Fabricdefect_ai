# Crumble Vision AI — Architecture Documentation

> **Project:** Crumble Vision AI (a.k.a. "Crumb Studio AI")
> **Purpose:** Single-page web application that lets a user upload a cookie/biscuit image, annotate a region, describe a synthetic defect with a text prompt, and receive an AI-edited image back for side-by-side comparison and download.
> **Scope:** MVP with two parallel workstreams — (A) UI + Backend + in-house annotation tool, (B) AI model fine-tuning (integration point documented below).

---

## 1. High-Level Overview

Crumble Vision AI is a **monorepo** split into two top-level workspaces:

```
Crumble_VisionAI/
├── Backend/            # FastAPI (Python) API server + ML inference
├── frontend/           # React + Vite + Konva single-page app
└── docs/               # Architecture, decisions, setup guides
```

```
                    ┌─────────────────────────────┐
   Browser (React)  │        frontend/ (SPA)       │
   ────────────────▶│  Upload ▸ Annotate ▸ Prompt  │
                    │  ▸ Generate ▸ Compare ▸ DL   │
                    └───────────────┬───────────────┘
                                    │  HTTPS (JSON + base64 PNG)
                                    ▼
                    ┌─────────────────────────────┐
                    │   Backend/ (FastAPI)         │
                    │  /api/v1/images              │
                    │  /api/v1/sam                 │  ──▶ MobileSAM (box-prompt)
                    │  /api/v1/generations         │  ──▶ Synthetic defect engine
                    └──────┬───────────────┬───────┘
                           │               │
                           ▼               ▼
                  ┌─────────────┐   ┌──────────────────────┐
                  │ PostgreSQL  │   │ Local filesystem      │
                  │ (Supabase)  │   │ storage/ (uploads,    │
                  │             │   │ masks, results)       │
                  └─────────────┘   └──────────────────────┘
```

The MVP is **deliberately structured** so that Workstream A (the app) is fully demo-ready with a stub generation engine, and Workstream B's real fine-tuned model can be swapped into `generation_service.generate_defect()` later without any frontend or contract changes.

---

## 2. Backend Architecture (`Backend/`)

The backend is a **FastAPI** application (ASGI) served with **Uvicorn**. It owns: image upload/validation, filesystem storage, the PostgreSQL data layer, the MobileSAM segmentation service, and the (currently stubbed) defect-generation service.

### 2.1 Technology Stack

| Concern | Technology |
|---|---|
| Web framework | FastAPI `0.115.0` |
| ASGI server | Uvicorn (standard) `0.30.6` |
| ORM / DB toolkit | SQLAlchemy `2.0.35` |
| Validation / settings | Pydantic `2.9.2`, `pydantic-settings` `2.5.2` |
| Form/multipart parsing | `python-multipart` `0.0.9` |
| Image processing | Pillow `10.4.0`, NumPy `1.26.4` |
| Database driver | `psycopg2-binary` `2.9.9` (PostgreSQL) |
| Segmentation model | `torch` `2.4.1`, `torchvision` `0.19.1`, `mobile_sam` (GitHub: ChaoningZhang/MobileSAM) |
| HTTP client (future Roboflow) | `httpx` `0.27.2` |
| Tests | `pytest` `8.3.3` |

Pinned versions are declared in both `requirements.txt` and `pyproject.toml`.

### 2.2 Application Entry Point — `app/main.py`

On startup (`main.py`):
1. Reads settings via `get_settings()` (lru-cached pydantic-settings).
2. Creates required directories: `storage/uploads`, `storage/results`, `storage/masks`, `storage`.
3. Calls `Base.metadata.create_all(bind=engine)` to create tables from SQLAlchemy models.
4. Runs `run_migrations()` to apply any pending SQL migrations.
5. Checks for the MobileSAM checkpoint (`app/ml/sam/weights/mobile_sam.pt`); emits a **warning** (not a crash) if missing — `/api/v1/sam/segment` will then return `503` until downloaded.
6. Mounts the FastAPI app, CORS middleware (`allow_origins=["*"]` — permissive for local/dev), and routers under `/api/v1`.
7. Mounts the `storage/` directory as static files at `/storage` so generated results and masks are directly servable.
8. Exposes `GET /health` → `{"status": "ok"}`.

Routers mounted:
- `images.router` → `/api/v1/i
mages`
- `generations.router` → `/api/v1/generations`
- `sam.router` → `/api/v1/sam`

### 2.3 Configuration — `app/core/config.py` + `.env`

Settings are loaded from `Backend/.env` (gitignored; template in `Backend/env.example`) via `pydantic-settings`.

| Setting | Default | Purpose |
|---|---|---|
| `APP_NAME` | `Crumb Studio AI Backend` | Display name |
| `DATABASE_URL` | `""` (required) | SQLAlchemy URL — `postgresql+psycopg2://…` (Supabase) |
| `UPLOAD_DIR` | `storage/uploads` | Where uploaded originals are stored |
| `MAX_UPLOAD_SIZE_MB` | `10` | Upload size limit |
| `ALLOWED_IMAGE_CONTENT_TYPES` | `image/jpeg`, `image/png` | Accepted upload types |
| `ROBOFLOW_API_KEY` / `_WORKSPACE` / `_PROJECT` | `""` | Reserved for optional Roboflow integration (not currently on critical path) |
| `ROBOFLOW_API_BASE` | `https://api.roboflow.com` | Roboflow REST base |
| `ROBOFLOW_APP_BASE` | `https://app.roboflow.com` | Roboflow app base |
| `SAM_WEIGHTS_DIR` | `app/ml/sam/weights` | MobileSAM checkpoint directory |

> **Note:** Roboflow config keys exist but the current design chose an **in-house annotation tool** over Roboflow (see `docs/annotation-tool-decision.md`), so they are currently unused on the critical path.

### 2.4 Database Layer

**Engine & session** — `app/db/session.py`:
- `create_engine(settings.DATABASE_URL, connect_args={"sslmode": "require"}, pool_pre_ping=True)`
- `sslmode: require` is required by Supabase PostgreSQL endpoints.
- `pool_pre_ping=True` avoids "server closed the connection unexpectedly" errors against Supabase's connection pooler.
- `SessionLocal` is a `sessionmaker` (autocommit=False, autoflush=False).

**Base** — `app/db/base.py`: `declarative_base()` from SQLAlchemy ORM.

**Models** — `app/db/models.py`:
- **`Image`** table (`images`):
  - `id` (String PK, UUID v4 from storage layer)
  - `original_filename`, `content_type`, `size_bytes`, `storage_path`
  - `roboflow_image_id` (nullable — set if/when pushed to Roboflow)
  - `created_at` (UTC timestamp)
- **`Generation`** table (`generations`):
  - `id` (String PK, UUID v4)
  - `image_id` (FK → `images.id`, indexed)
  - `prompt` (text, ≤1000 chars)
  - `mask_reference` (path to stored mask PNG)
  - `status` (`pending` → `processing` → `complete` / `failed`)
  - `result_path` (path to generated result PNG)
  - `error_message`
  - `created_at`, `updated_at` (UTC)

**Repository** — `app/db/repository.py`: Thin data-access functions used by services/routers:
- `create_image_record`, `get_image_by_id`, `update_image_roboflow_id`
- `create_generation_record`, `update_generation_record`, `get_generation_by_id`

**Migrations** — `app/db/migrate.py`: A lightweight, dependency-free SQL migration runner.
- Reads `*.sql` files from `app/db/migrations/` in sorted order.
- Tracks applied migrations in a `_migrations` table (auto-created).
- Skips migrations already applied — safe to run on every startup.
- Existing migration: `001_add_roboflow_image_id.sql` (adds the `roboflow_image_id` column to `images`).

### 2.5 Storage — `app/core/storage.py`

Filesystem-backed storage, abstracted behind small classes so it can later be swapped for S3/GCS without touching callers:
- **`LocalImageStorage`**: `save(file_bytes, extension)` → writes raw bytes to `UPLOAD_DIR/{uuid}{ext}`, returns `(image_id, storage_path)`. `path_for(image_id, extension)` resolves the path.
- **`LocalMaskStorage`**: `save(file_bytes, generation_id)` → writes mask PNG to `storage/masks/{generation_id}.png`.
- Helpers `get_storage()` / `get_mask_storage()`.

### 2.6 Dependency Injection — `app/core/dependencies.py`

`get_db()` is a FastAPI dependency generator yielding a `SessionLocal()` and closing it after the request.

### 2.7 Services

#### Image Service — `app/services/image_service.py`
`process_upload(db, file)`:
- Rejects unsupported content types (only JPG/PNG) → raises `UnsupportedFileTypeError`.
- Reads bytes, rejects empty files.
- Enforces `MAX_UPLOAD_SIZE_MB`.
- Delegates to storage + repository to persist the `Image` record.
- Returns the ORM record.

#### SAM Service — `app/services/sam_service.py` (AI #1)
`segment_within_box(source_path, image_id, box, point=None)`:
- Loads the source image to get `(width, height)`.
- Calls `predict_mask()` from the ML predictor (see §2.8).
- **Safety guarantee:** SAM can only *tighten* the boundary inward. The raw SAM mask is intersected (`AND`) with a rasterized version of the user's box (`_rasterize_box`), so the editable region is **never** larger than the user's selection — preventing edge bleed.
- Writes a human-readable debug preview to `storage/results/mask_preview_<image_id>.png` (black=selected, white=rest — inverse of the real contract, for visual scanning only).
- Returns the real mask as a **black/white PNG** (white = editable region) as raw bytes — matching the manual brush/polygon mask contract exactly, so `generation_service` needs no special-casing.

#### Generation Service — `app/services/generation_service.py` (AI #2 — currently a STUB)
`generate_defect(source_path, mask_path, generation_id, prompt)`:
- Loads the mask (white = editable) and resizes to source dimensions with nearest-neighbor.
- Until Workstream B delivers the real model, it applies a **synthetic effect** chosen by prompt keyword:
  - `burned` → `_apply_burn_effect` (darken/burn with brownish-black gradient)
  - `cracked` → `_apply_crack_effect` (crack lines)
  - `moldy` → `_apply_mold_effect` (greenish mold spots)
  - `chocolate`/`chocolate chips` → `_apply_chocolate_chips_effect`
  - `underbaked` → `_apply_underbaked_effect` (pale/doughy)
  - `broken`/`broken edge` → `_apply_broken_edge_effect` (jagged missing chunks)
  - anything else → `_apply_generic_effect` (per-pixel noise)
- The effect is applied **only within the white mask region**; the rest of the image is untouched.
- Saves `storage/results/result_<generation_id>.png` and returns its path.
- **Swap point:** when the real model is ready, replace the body of `generate_defect()` with a call to the served model endpoint — no frontend/contract change required.

### 2.8 MobileSAM ML Predictor — `app/ml/sam/predictor.py`

A thin, cached wrapper around MobileSAM (`mobile_sam` package). Contains **only** model loading + raw inference — no HTTP/DB/response shaping.
- `_MODEL_TYPE = "vit_t"` (TinyViT backbone).
- `_CHECKPOINT = {SAM_WEIGHTS_DIR}/mobile_sam.pt` (downloaded via `scripts/download_sam_weights.py`).
- `_load_model()` lazily loads MobileSAM onto `cuda` if available, else `cpu`, under a `threading.Lock`.
- `_ensure_image_encoded()` runs the expensive image encoder **once per image**, cached by `image_id` (`_loaded_image_id`).
- `predict_mask(source_path, image_id, box, point=None)`:
  - Requires at least one of `box` (`[x0,y0,x1,y1]`) or `point`.
  - Runs `predictor.predict(box=..., point_coords=..., multimask_output=False)` — single best mask (a box prompt removes the ambiguity a point-only flow had).
  - Returns a boolean `(H,W)` array, `True` = segmented/editable region.

**Checkpoint acquisition:** `scripts/download_sam_weights.py` downloads `mobile_sam.pt` (~38–40 MB) from the MobileSAM GitHub repo into `app/ml/sam/weights/`. It validates size and re-downloads if a partial/corrupt file is found. Also available as `scripts/download_sam_weights.sh`.

### 2.9 API Routes (`app/api/v1/`)

| Route | Method | Purpose | Key behavior |
|---|---|---|---|
| `/api/v1/images/upload` | POST | Upload image (KPI 2) | Validates type/size, stores file, creates `Image` row, returns `ImageUploadResponse` (201). Errors: 415 (bad type), 413 (too large). |
| `/api/v1/sam/segment` | POST | MobileSAM segmentation (box-prompted) | Body `{image_id, box:[x0,y0,x1,y1], point?:{x,y}}`. Returns `{mask_data: "data:image/png;base64,..."}` (white = editable). Errors: 404 (no image), 400 (bad box), 503 (no checkpoint), 500 (inference fail). |
| `/api/v1/generations` | POST | Generate defect (KPI 9) | Body `{image_id, prompt, mask_data(base64 PNG)}`. Creates `Generation` row, decodes+stores mask, runs `generate_defect()`, updates status to `complete`/`failed`, returns `GenerationResponse` with `result_url` (201). |
| `/api/v1/generations/{id}` | GET | Get generation status/result | Returns `GenerationResponse` (or 404). |

> **Note:** `app/api/v1/auth.py` exists in the tree but currently contains no routes (no auth layer is implemented in the MVP — appropriate for a local/demo single-page tool).

**Schemas** (`app/schemas/`):
- `image.py`: `ImageUploadResponse`, `ErrorResponse`.
- `generation.py`: `GenerationRequest` (`image_id`, `prompt` ≤1000, `mask_data`), `GenerationResponse` (`id`, `image_id`, `prompt`, `status`, `result_url?`, `error_message?`, timestamps).

---

## 3. AI Services Summary

| Service | Technology | Role | Status |
|---|---|---|---|
| **Segmentation (SAM)** | MobileSAM (`vit_t` TinyViT) via PyTorch | Box-prompted region segmentation; tightens user's rough box into a precise editable mask, clipped to the box. | **Active** — lazy-loaded on first `/sam/segment` call. |
| **Defect Generation** | Synthetic effect engine (prompt-keyword → NumPy/Pillow effect) | Applies a defect-like transformation only inside the mask region. | **STUB** — placeholder until Workstream B's fine-tuned model is served; swap point is `generation_service.generate_defect()`. |
| **(Reserved) Roboflow** | Roboflow REST API via `httpx` | Originally planned hosted annotation; replaced by in-house Konva tool. Config keys retained for optional future use. | Not on critical path. |

**Mask contract (shared by all paths):**
- PNG at the **exact pixel dimensions** of the source image.
- **White** (`#FFFFFF`) = region to edit (editable).
- **Black** (`#000000`) = protected / untouched.
- Used identically whether produced by the manual brush/rect/polygon tool (client-side) or by MobileSAM (server-side).

> ### Does a model generate the annotation mask?
> **Only on the optional AI-assisted path — not on the manual path.**
> - **Manual mask (brush / eraser / rectangle / polygon):** NO model. The mask is a deterministic, client-side rasterization of the user's drawn shapes (`maskEngine.rasterizeMask`). Pure geometry, no inference.
> - **AI-assisted mask ("AI Select" box tool):** YES. The frontend sends the user's box to `POST /api/v1/sam/segment`; the backend runs **MobileSAM** (`app/ml/sam/predictor.py`, `vit_t` TinyViT via PyTorch) constrained to that box, clips the result to the box, and returns a black/white PNG mask. MobileSAM is the model that generates this mask.
>
> **Separate concern — the defect-generation model:** The model that *edits* the image inside the mask (`generation_service.generate_defect`) is **currently a STUB** (synthetic NumPy/Pillow effects). The real fine-tuned defect model (Workstream B) is not yet wired in; its swap point is `generation_service.generate_defect()`.

---

## 4. Frontend Architecture (`frontend/`)

A **React 19 + Vite** single-page application. The entire product is one page (`StudioPage`) implementing the upload → annotate → prompt → generate → compare → download flow.

### 4.1 Technology Stack

| Concern | Technology |
|---|---|
| Framework | React `^19.2` |
| Build tool | Vite `^8.1` (`@vitejs/plugin-react`) |
| Canvas / annotation | `konva` `^10.3` + `react-konva` `^19.2` |
| Icons | `lucide-react` |
| Styling | Tailwind CSS `^3.4` + PostCSS + Autoprefixer |
| Lint | ESLint `^10` (+ react-hooks, react-refresh plugins) |

### 4.2 Key Directories

```
frontend/src/
├── App.jsx                      # Mounts StudioPage
├── main.jsx                     # React entry
├── pages/
│   └── StudioPage.jsx           # Single-page layout & flow orchestration
├── components/studio/
│   ├── Header.jsx
│   ├── UploadPanel.jsx          # Drag/drop + browse upload (KPI 4)
│   ├── AnnotationPanel.jsx      # Wraps annotation workspace (KPI 5/6/7)
│   ├── annotation/
│   │   ├── AnnotationCanvas.jsx # Konva canvas (brush/eraser/rect/polygon/AI-select)
│   │   └── Toolbar.jsx          # Tool/brush/undo/redo/zoom/clear controls
│   ├── PromptInput.jsx          # Defect prompt text (KPI 8)
│   ├── GenerateButton.jsx       # Generate trigger (KPI 10)
│   ├── ProgressIndicator.jsx    # Loading state
│   ├── ComparisonView.jsx       # Original vs generated (KPI 12)
│   └── DownloadButton.jsx       # Result download (KPI 13)
├── lib/annotation/
│   └── maskEngine.js            # Pure rasterizer: shapes → black/white PNG mask
├── hooks/
│   └── useAnnotationHistory.js  # Undo/redo shape-history state
├── state/
│   └── studioStore.js           # Single source of truth for the studio flow
├── services/
│   └── api.js                   # REST client for the backend
└── styles/globals.css
```

### 4.3 State Management — `state/studioStore.js`

A single `useStudioState()` hook (React `useState`) is the source of truth:
- `image` `{ id, file, name, size, previewUrl }`
- `mask` `{ id, previewUrl, dataUrl }`
- `prompt`, `status` (IDLE → UPLOADED → ANNOTATING → MASK_READY → GENERATING → COMPLETE/FAILED), `result`, `error`.
- `reset()` clears everything.

`StudioPage.jsx` orchestrates: on image change → `UPLOADED`; `canGenerate` requires image + mask + non-empty prompt + not generating; `handleGenerate` calls `generateImage(...)` and sets `COMPLETE`/`FAILED`.

### 4.4 Annotation Tool (In-House Konva) — KPI 5/6/7

Decided in `docs/annotation-tool-decision.md` to **build in-house** (React + Konva) rather than embed Roboflow/CVAT. Rationale: keep the user in-app, full UX control, no third-party account/API dependency.

- **`AnnotationCanvas.jsx`** (react-konva): renders the uploaded image on a canvas with brush, eraser, rectangle, polygon, and an AI-select (box) tool. Supports zoom (scroll) and pan. Commits shapes to history.
- **`useAnnotationHistory.js`**: manages committed-shape list with undo/redo (one committed shape per step) and clear-all — standard editor semantics (drawing after undo discards redo branch).
- **`maskEngine.js`** (`rasterizeMask`): deterministic, framework-agnostic rasterizer.
  - Starts fully black, paints white for each shape (brush/rect/polygon), uses `destination-out` for eraser variants.
  - Flattens transparency back to black so the exported PNG is clean two-tone.
  - **Output dimensions exactly match the source image's natural size**, regardless of zoom.
  - `hasPaintedRegion()` prevents treating an all-black (nothing/erased) canvas as a ready mask.
  - The resulting data URL is handed up via `onMaskChange({ dataUrl, previewUrl })`.
- **AI Select tool:** `AnnotationPanel.handleSamBoxReady` calls `segmentWithSam({ imageId, box })` → backend returns a MobileSAM mask data URL, which is fed into the **same** `{ dataUrl, previewUrl }` contract, so Generate works unchanged. (The SAM path bypasses shape history entirely.)

### 4.5 Backend Communication — `services/api.js`

REST client wrapping `fetch` to the FastAPI backend:
- `uploadImage(file)` → `POST /api/v1/images/upload`
- `generateImage({ imageId, prompt, maskDataUrl })` → `POST /api/v1/generations`
- `segmentWithSam({ imageId, box })` → `POST /api/v1/sam/segment`
- Handles JSON + base64 PNG payloads and structured errors.

---

## 5. End-to-End Data Flow

### 5.1 Manual Annotation Flow
1. User selects/drops an image in `UploadPanel` → `POST /api/v1/images/upload` (validates, stores file, creates `Image` row) → returns `image_id`.
2. `AnnotationPanel` loads the image on a Konva canvas. User paints a region (brush/eraser/rect/polygon).
3. `maskEngine.rasterizeMask()` produces a black/white PNG (`dataUrl`) at source resolution → stored in `studioStore.mask`.
4. User enters a prompt (`PromptInput`).
5. `GenerateButton` → `POST /api/v1/generations` with `{image_id, prompt, mask_data}`:
   - Backend verifies image, creates `Generation` (status `pending`), decodes+stores mask PNG, sets `processing`.
   - `generate_defect()` applies the synthetic effect **only inside the white mask**.
   - Saves `storage/results/result_<id>.png`, sets `complete`, returns `result_url` = `/storage/results/result_<id>.png`.
6. `ComparisonView` shows original vs generated side-by-side; `DownloadButton` downloads the result PNG.

### 5.2 AI-Assisted (MobileSAM) Annotation Flow
1. Steps 1 above (upload).
2. User picks the **AI Select** tool and drags a box over the rough region.
3. `AnnotationPanel.handleSamBoxReady` → `POST /api/v1/sam/segment` `{image_id, box, point?}`.
4. Backend: `sam_service.segment_within_box` → `predict_mask` (MobileSAM) → clipped to box → returns a black/white PNG mask `data:image/png;base64,...` (white = editable).
5. Frontend stores that mask in `studioStore.mask` (same contract as manual drawing), and the rest of the flow (prompt → generate → compare → download) proceeds identically.

### 5.3 Mask Contract (Critical Invariant)

Both annotation paths produce an identical mask consumed by `/api/v1/generations`:

| Property | Value |
|---|---|
| Format | PNG |
| Dimensions | Exactly the source image's natural width × height |
| White (`#FFFFFF`) | Region the AI will modify (editable) |
| Black (`#000000`) | Protected / left unchanged |
| Transport | Base64 data URL (`data:image/png;base64,...`) in `mask_data` |

This contract must **not** be inverted on either side without coordinated changes to both `maskEngine.js` (`rasterizeMask`) and `generation_service._load_mask`.

---

## 6. Database Schema

### 6.1 `images`
| Column | Type | Notes |
|---|---|---|
| `id` | VARCHAR(36) PK | UUID v4 (from storage layer) |
| `original_filename` | VARCHAR(255) | Not null |
| `content_type` | VARCHAR(50) | Not null |
| `size_bytes` | INTEGER | Not null |
| `storage_path` | VARCHAR(500) | Not null — absolute path on disk |
| `roboflow_image_id` | VARCHAR(64) | Nullable — set if pushed to Roboflow |
| `created_at` | TIMESTAMP | UTC default |

### 6.2 `generations`
| Column | Type | Notes |
|---|---|---|
| `id` | VARCHAR(36) PK | UUID v4 default |
| `image_id` | VARCHAR(36) FK → `images.id` | Indexed, not null |
| `prompt` | VARCHAR(1000) | Not null |
| `mask_reference` | VARCHAR(500) | Nullable — path to mask PNG |
| `status` | VARCHAR(20) | `pending` → `processing` → `complete` / `failed` |
| `result_path` | VARCHAR(500) | Nullable — path to result PNG |
| `error_message` | VARCHAR(1000) | Nullable |
| `created_at` | TIMESTAMP | UTC default |
| `updated_at` | TIMESTAMP | UTC, updated on change |

### 6.3 Migration Tracking
`_migrations` (filename PK, applied_at) — managed by `app/db/migrate.py`.

---

## 7. Complete File & Directory Layout

This section documents the **full, detailed folder structure** of the monorepo as it exists in the repository.

### 7.1 Monorepo Root

```
Crumble_VisionAI/
├── .gitignore
├── annotation-tool.patch         # Git patch capturing the in-house annotation tool changes
├── KPI_Plan.md                   # KPI definitions + Workstream A/B integration gate
├── README.md
├── package-lock.json             # Root lockfile (legacy/shared tooling)
├── .pytest_cache/                # Pytest cache (gitignored)
├── storage/                      # Runtime uploads (when backend is launched from repo root)
├── Backend/                      # FastAPI backend + ML inference
├── frontend/                     # React + Vite single-page app
├── docs/                         # Architecture, decisions, SRS
└── ai_experiments/               # Research / model experimentation
```

### 7.2 Backend (`Backend/`)

```
Backend/
├── app/
│   ├── main.py                  # App entry, routers, static mount, startup
│   ├── __init__.py
│   ├── ai_client/
│   │   └── inference_client.py  # Client to the (future) fine-tuned model endpoint
│   ├── core/
│   │   ├── config.py            # Pydantic settings (DATABASE_URL, upload limits, SAM/Roboflow)
│   │   ├── dependencies.py      # get_db() session dependency
│   │   ├── security.py          # (reserved) password hashing / JWT helpers
│   │   └── storage.py           # LocalImageStorage / LocalMaskStorage
│   ├── db/
│   │   ├── base.py              # declarative_base
│   │   ├── session.py           # engine (Supabase/PostgreSQL), SessionLocal
│   │   ├── models.py            # Image, Generation ORM models
│   │   ├── repository.py        # CRUD data-access functions
│   │   ├── migrate.py           # SQL migration runner
│   │   └── migrations/
│   │       └── 001_add_roboflow_image_id.sql
│   ├── schemas/
│   │   ├── image.py             # ImageUploadResponse, ErrorResponse
│   │   ├── generation.py        # GenerationRequest, GenerationResponse
│   │   ├── auth.py              # (reserved) auth schemas
│   │   ├── user.py              # (reserved) user schemas
│   │   ├── analytics.py         # (reserved) analytics schemas
│   │   └── detection.py         # (reserved) detection schemas
│   ├── services/
│   │   ├── image_service.py     # upload validation + persistence
│   │   ├── sam_service.py       # MobileSAM box-constrained segmentation
│   │   ├── generation_service.py# synthetic defect engine (STUB for real model)
│   │   ├── auth_service.py      # (reserved) auth service
│   │   ├── user_service.py      # (reserved) user service
│   │   ├── analytics_service.py # (reserved) analytics service
│   │   └── detection_service.py # (reserved) detection service
│   ├── ml/
│   │   ├── __init__.py
│   │   └── sam/
│   │       ├── __init__.py
│   │       ├── predictor.py     # cached MobileSAM wrapper (load + infer)
│   │       └── weights/
│   │           └── mobile_sam.pt  # checkpoint (~40MB, gitignored, downloaded)
│   ├── api/
│   │   └── v1/
│   │       ├── images.py        # POST /upload
│   │       ├── sam.py           # POST /segment
│   │       ├── generations.py   # POST /, GET /{id}
│   │       ├── auth.py          # (reserved) auth routes
│   │       ├── users.py         # (reserved) user routes
│   │       ├── analytics.py     # (reserved) analytics routes
│   │       └── detections.py    # (reserved) detection routes
│   └── storage/                 # runtime: results/ (mask preview PNGs)
├── storage/                     # runtime: uploads/, masks/, results/
├── scripts/
│   ├── download_sam_weights.py  # checkpoint downloader (cross-platform, Python)
│   └── download_sam_weights.sh  # checkpoint downloader (bash)
├── tests/
│   ├── conftest.py              # shared pytest fixtures/config
│   ├── test_images.py           # upload/validation tests
│   ├── test_sam.py              # MobileSAM segmentation tests
│   ├── test_generations.py      # generation flow tests
│   └── test_migration.py        # migration runner tests
├── ai_experiments/
│   └── mobilesam_test/          # MobileSAM research clone + experiments
│       ├── test_mobilesam.py    # standalone SAM experiment script
│       ├── test_images/         # sample cookie images for experiments
│       │   └── cookie1.jpeg
│       └── MobileSAM/           # vendored MobileSAM repo (research only)
│           ├── mobile_sam/       # original MobileSAM package
│           ├── MobileSAMv2/      # experimental v2 (EfficientViT-based)
│           ├── app/              # demo Gradio app
│           ├── scripts/          # export / AMG utilities
│           ├── notebooks/        # example notebooks
│           ├── assets/           # diagrams and sample images
│           ├── weights/          # mobile_sam.pt (research copy)
│           └── ...               # (README, LICENSE, setup.py, etc.)
├── docs/
│   └── mobilesam-setup.md       # MobileSAM install & troubleshooting
├── requirements.txt             # pinned Python dependencies
├── pyproject.toml              # project metadata + tooling config
├── env.example                 # template for .env
├── crumb_studio.db             # local SQLite dev DB (gitignored)
└── .env                        # (gitignored) real credentials
```

> **Note:** Files marked **(reserved)** exist in the tree but are not yet wired into the MVP runtime (auth, users, analytics, detections). They are scaffolding for the future expansion described in §9.

### 7.3 Frontend (`frontend/`)

```
frontend/
├── index.html                  # Vite HTML entry
├── package.json                # npm dependencies & scripts
├── package-lock.json
├── vite.config.js              # Vite dev/build config
├── eslint.config.js            # ESLint flat config
├── tailwind.config.js          # Tailwind CSS config
├── postcss.config.js           # PostCSS (Tailwind + Autoprefixer)
├── README.md
├── .gitignore
├── dist/                       # production build output (gitignored)
└── src/
    ├── main.jsx                # React entry point
    ├── App.jsx                 # Mounts StudioPage
    ├── pages/
    │   └── StudioPage.jsx      # Single-page flow orchestration
    ├── components/studio/
    │   ├── Header.jsx          # App header / branding
    │   ├── UploadPanel.jsx     # Drag/drop + browse upload (KPI 4)
    │   ├── AnnotationPanel.jsx # Wraps annotation workspace (KPI 5/6/7)
    │   ├── annotation/
    │   │   ├── AnnotationCanvas.jsx  # Konva canvas (brush/eraser/rect/polygon/AI-select)
    │   │   └── Toolbar.jsx          # Tool/brush/undo/redo/zoom/clear controls
    │   ├── PromptInput.jsx     # Defect prompt text (KPI 8)
    │   ├── GenerateButton.jsx  # Generate trigger (KPI 10)
    │   ├── ProgressIndicator.jsx    # Loading state
    │   ├── ComparisonView.jsx  # Original vs generated (KPI 12)
    │   └── DownloadButton.jsx  # Result download (KPI 13)
    ├── lib/annotation/
    │   └── maskEngine.js        # Pure rasterizer: shapes → black/white PNG mask
    ├── hooks/
    │   └── useAnnotationHistory.js  # Undo/redo shape-history state
    ├── state/
    │   └── studioStore.js       # Single source of truth for the studio flow
    ├── services/
    │   └── api.js               # REST client for the backend
    └── styles/
        └── globals.css          # Tailwind directives + global styles
```

### 7.4 Docs (`docs/`)

```
docs/
├── ARCHITECTURE.md              # This document
├── annotation-tool-decision.md  # Build-vs-Roboflow-vs-CVAT rationale
└── FabricDefect_AI_Architecture_SRS.pdf  # Supplementary SRS reference
```

---

## 8. Setup & Run

### 8.1 Backend
```bash
cd Backend
python -m venv .venv && source .venv/bin/activate   # or: .venv\Scripts\activate (Windows)
pip install -r requirements.txt
cp env.example .env          # then fill in DATABASE_URL (Supabase PostgreSQL)
bash scripts/download_sam_weights.sh        # fetch MobileSAM checkpoint (~40MB)
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```
- Health: `GET http://localhost:8000/health`
- API docs: `http://localhost:8000/docs`

### 8.2 Frontend
```bash
cd frontend
npm install
npm run dev                 # Vite dev server (default http://localhost:5173)
```
Configure the API base URL in `frontend/src/services/api.js` to point at the backend (e.g. `http://localhost:8000`).

### 8.3 MobileSAM Notes
- Model loads **lazily** on the first `/api/v1/sam/segment` call (not at boot).
- Requires `torch`, `torchvision`, `numpy`, and the `mobile_sam` package (installed from GitHub).
- If the checkpoint is missing, the endpoint returns `503` with a clear message (see `Backend/docs/mobilesam-setup.md`).

---

## 9. Key Design Decisions & Integration Gate

- **Two workstreams:** UI/Backend (A) and Model fine-tuning (B) are built in parallel. A is demo-ready against the stub; B swaps into `generation_service.generate_defect()` at the integration gate (see `KPI_Plan.md`).
- **In-house annotation tool** over Roboflow/CVAT (see `docs/annotation-tool-decision.md`): keeps users in-app, no external dependency, full UX control.
- **Box-clipped SAM:** MobileSAM output is intersected with the user's box so it can only tighten boundaries inward — prevents edge bleed outside the selection.
- **Mask contract invariance:** a single PNG (white=editable) contract shared by client rasterizer and server generation, so neither side needs to know how the other produced the mask.
- **Storage abstraction:** filesystem now, swappable to S3/GCS later via `LocalImageStorage`/`LocalMaskStorage` interfaces.
- **No auth in MVP:** appropriate for a local/demo single-page tool; `auth.py` is a placeholder for future expansion.
- **Migrations without Alembic:** a tiny SQL-file runner (`app/db/migrate.py`) keeps schema evolution dependency-free and repeatable.

---

## 10. References

- `KPI_Plan.md` — KPI definitions and the Workstream A/B integration gate.
- `docs/annotation-tool-decision.md` — build-vs-Roboflow-vs-CVAT rationale.
- `Backend/docs/mobilesam-setup.md` — MobileSAM install & troubleshooting.
- `requirements.txt` / `pyproject.toml` — pinned dependency versions.
- `env.example` — required environment variables.
