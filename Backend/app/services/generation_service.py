
# Repo path: Backend/app/services/generation_service.py
"""
Masked generation service.

Applies a synthetic defect (defined by prompt) ONLY within the region
specified by the user's mask, keeping the rest of the image untouched.

Until Workstream B delivers the real fine-tuned model, this generates
a constrained effect that demonstrates the mask boundary is respected.
When the real model is ready, swap the logic in generate_defect() for
a call to the served model endpoint.
"""
import logging
from pathlib import Path

import numpy as np
import torch
from diffusers import StableDiffusionXLInpaintPipeline
from PIL import Image, ImageFilter

logger = logging.getLogger(__name__)

# Points at Synthetic_AI/3_models relative to this file's location.
# __file__ = .../Crumble_VisionAI/Backend/app/services/generation_service.py
# parents[0]=services/, parents[1]=app/, parents[2]=Backend/, parents[3]=Crumble_VisionAI/
_SYNTHETIC_AI_ROOT = Path(__file__).resolve().parents[3] / "Synthetic_AI"
_MODEL_PATH = _SYNTHETIC_AI_ROOT / "3_models" / "stable-diffusion-xl-1.0-inpainting-0.1"
_LORA_DIR = _SYNTHETIC_AI_ROOT / "3_models"
_LORA_FILENAME = "cookie_defect_lora.safetensors"

_pipe = None


def _load_pipeline():
    """Lazily load the SDXL inpainting pipeline once. Uses the LoRA if
    present, otherwise runs the base model only (fine — your friend hasn't
    trained the LoRA yet)."""
    global _pipe
    if _pipe is None:
        if not _MODEL_PATH.exists():
            raise RuntimeError(
                f"Base model not found at {_MODEL_PATH}. Run "
                "`python Synthetic_AI/4_scripts/download_model.py` first."
            )

        device = "cuda" if torch.cuda.is_available() else "cpu"
        dtype = torch.float16 if device == "cuda" else torch.float32
        logger.info("Loading SDXL inpainting pipeline on %s...", device)

        _pipe = StableDiffusionXLInpaintPipeline.from_pretrained(
            str(_MODEL_PATH), torch_dtype=dtype, local_files_only=True,
        )
        if device == "cuda":
            _pipe.enable_model_cpu_offload()
        _pipe.enable_attention_slicing()
        _pipe.enable_vae_slicing()

        lora_full_path = _LORA_DIR / _LORA_FILENAME
        if lora_full_path.exists():
            _pipe.load_lora_weights(str(_LORA_DIR), weight_name=_LORA_FILENAME)
            logger.info("Loaded fine-tuned LoRA weights.")
        else:
            logger.info("No LoRA found yet — running base model only.")
    return _pipe


def _generate_with_real_model(source: Image.Image, mask_img: Image.Image, prompt: str) -> Image.Image:
    pipe = _load_pipeline()

    init_image = source.resize((1024, 1024))
    mask_gray = mask_img.convert("L").resize((1024, 1024))
    mask_array = [255 if px > 20 else 0 for px in mask_gray.getdata()]
    mask_clean = Image.new("L", mask_gray.size)
    mask_clean.putdata(mask_array)
    mask_clean = mask_clean.filter(ImageFilter.GaussianBlur(radius=12))

    result = pipe(
        prompt=prompt,
        negative_prompt="blurry, smooth, plastic texture, cartoon, drawing, 3d render",
        image=init_image,
        mask_image=mask_clean,
        height=1024, width=1024,
        strength=0.95, guidance_scale=7.0, num_inference_steps=40,
    ).images[0]

    return result.resize(source.size)  # scale back to original dimensions

# IMPORTANT: This must resolve to the SAME directory that the `/storage`
# StaticFiles mount in `app/main.py` serves (it uses `Path("storage").resolve()`,
# i.e. a CWD-relative path). If we wrote results under the package root
# (`Backend/storage/...`) while the mount serves `<cwd>/storage/...`, the two
# would diverge whenever the app is launched from a directory other than
# `Backend/`, the frontend's `/storage/results/...` <img> would 404, and the
# generated image would never appear in ComparisonView. Keeping both
# CWD-relative guarantees they always align.
_RESULT_DIR = Path("storage/results").resolve()


def _load_mask(mask_path: str, target_size: tuple[int, int]) -> np.ndarray:
    """Load the mask from disk and resize to target_size (W, H). Returns a
    boolean array where True = region the user painted (editable)."""
    mask_img = Image.open(mask_path).convert("L")
    mask_img = mask_img.resize(target_size, Image.Resampling.NEAREST)
    mask_arr = np.array(mask_img)
    return mask_arr > 128


def _apply_burn_effect(source: Image.Image, mask: np.ndarray) -> Image.Image:
    """Darken/burn the masked region with a brownish-black gradient."""
    result = np.array(source).copy()
    h, w = mask.shape
    rng = np.random.default_rng()
    for _ in range(max(1, h * w // 2000)):
        cx, cy = rng.integers(0, w), rng.integers(0, h)
        radius = rng.integers(5, 40)
        intensity = rng.integers(30, 120)
        color = (intensity, intensity // 3, intensity // 6)
        for y in range(max(0, cy - radius), min(h, cy + radius)):
            for x in range(max(0, cx - radius), min(w, cx + radius)):
                if (x - cx) ** 2 + (y - cy) ** 2 < radius**2 and mask[y, x]:
                    alpha = rng.uniform(0.3, 0.9)
                    result[y, x] = (result[y, x] * (1 - alpha) + np.array(color) * alpha).astype(np.uint8)
    return Image.fromarray(result)


def _apply_crack_effect(source: Image.Image, mask: np.ndarray) -> Image.Image:
    """Draw crack lines within the masked region."""
    result = np.array(source).copy()
    h, w = mask.shape
    rng = np.random.default_rng()
    for _ in range(rng.integers(3, 8)):
        for attempt in range(50):
            sx, sy = rng.integers(0, w), rng.integers(0, h)
            if mask[sy, sx]:
                break
        else:
            continue
        x, y = sx, sy
        length = rng.integers(20, 80)
        for _ in range(length):
            if not (0 <= x < w and 0 <= y < h) or not mask[y, x]:
                break
            result[y, x] = (20, 15, 10)
            if rng.random() < 0.15:
                dx = rng.integers(-2, 3)
                dy = rng.integers(-2, 3)
                nx, ny = x + dx, y + dy
                if 0 <= nx < w and 0 <= ny < h and mask[ny, nx]:
                    result[ny, nx] = (20, 15, 10)
            x += rng.integers(-1, 2)
            y += 1
    return Image.fromarray(result)


def _apply_mold_effect(source: Image.Image, mask: np.ndarray) -> Image.Image:
    """Add greenish mold spots within the masked region."""
    result = np.array(source).copy()
    h, w = mask.shape
    rng = np.random.default_rng()
    for _ in range(max(1, h * w // 1500)):
        cx, cy = rng.integers(0, w), rng.integers(0, h)
        if not mask[cy, cx]:
            continue
        radius = rng.integers(3, 25)
        for y in range(max(0, cy - radius), min(h, cy + radius)):
            for x in range(max(0, cx - radius), min(w, cx + radius)):
                if (x - cx) ** 2 + (y - cy) ** 2 < radius**2 and mask[y, x]:
                    alpha = rng.uniform(0.2, 0.7)
                    orig = result[y, x].astype(float)
                    mold = np.array([30, 120, 50])
                    result[y, x] = (orig * (1 - alpha) + mold * alpha).astype(np.uint8)
    return Image.fromarray(result)


def _apply_chocolate_chips_effect(source: Image.Image, mask: np.ndarray) -> Image.Image:
    """Add dark chocolate chip spots within the masked region."""
    result = np.array(source).copy()
    h, w = mask.shape
    rng = np.random.default_rng()
    for _ in range(max(1, h * w // 3000)):
        cx, cy = rng.integers(0, w), rng.integers(0, h)
        if not mask[cy, cx]:
            continue
        radius = rng.integers(4, 15)
        for y in range(max(0, cy - radius), min(h, cy + radius)):
            for x in range(max(0, cx - radius), min(w, cx + radius)):
                if (x - cx) ** 2 + (y - cy) ** 2 < radius**2 and mask[y, x]:
                    result[y, x] = (45, 25, 15)
    return Image.fromarray(result)


def _apply_underbaked_effect(source: Image.Image, mask: np.ndarray) -> Image.Image:
    """Make the masked region look pale/doughy (underbaked)."""
    result = np.array(source).copy()
    h, w = mask.shape
    for y in range(h):
        for x in range(w):
            if mask[y, x]:
                orig = result[y, x].astype(float)
                pale = np.array([240, 230, 200])
                result[y, x] = (orig * 0.4 + pale * 0.6).astype(np.uint8)
    return Image.fromarray(result)


def _apply_broken_edge_effect(source: Image.Image, mask: np.ndarray) -> Image.Image:
    """Create jagged missing chunks along the edge within the masked region."""
    result = np.array(source).copy()
    h, w = mask.shape
    rng = np.random.default_rng()
    for _ in range(max(1, h * w // 2000)):
        cx, cy = rng.integers(0, w), rng.integers(0, h)
        if not mask[cy, cx]:
            continue
        radius = rng.integers(5, 30)
        for y in range(max(0, cy - radius), min(h, cy + radius)):
            for x in range(max(0, cx - radius), min(w, cx + radius)):
                if (x - cx) ** 2 + (y - cy) ** 2 < radius**2 and mask[y, x]:
                    jitter = rng.integers(-3, 4)
                    if abs(x - cx) + abs(y - cy) + jitter > radius:
                        result[y, x] = (60, 40, 20)
    return Image.fromarray(result)


def _apply_generic_effect(source: Image.Image, mask: np.ndarray) -> Image.Image:
    """For custom prompts, apply a generic 'AI alteration' effect in the masked region."""
    result = np.array(source).copy()
    h, w = mask.shape
    rng = np.random.default_rng()
    noise = rng.integers(-20, 20, (h, w, 3), dtype=np.int16)
    for y in range(h):
        for x in range(w):
            if mask[y, x]:
                shifted = result[y, x].astype(np.int16) + noise[y, x]
                result[y, x] = np.clip(shifted, 0, 255).astype(np.uint8)
    return Image.fromarray(result)


_PROMPT_EFFECTS = {
    "burned": _apply_burn_effect,
    "cracked": _apply_crack_effect,
    "moldy": _apply_mold_effect,
    "chocolate chips": _apply_chocolate_chips_effect,
    "chocolate": _apply_chocolate_chips_effect,
    "underbaked": _apply_underbaked_effect,
    "broken edge": _apply_broken_edge_effect,
    "broken": _apply_broken_edge_effect,
}

def generate_defect(
    source_path: Path,
    mask_path: str,
    generation_id: str,
    prompt: str,
) -> Path:
    source = Image.open(source_path).convert("RGB")
    orig_size = source.size

    mask_arr = _load_mask(mask_path, orig_size)

    if not mask_arr.any():
        logger.warning("Mask is empty, returning original image")
        result = source
    else:
        try:
            mask_img = Image.open(mask_path).convert("L")
            result = _generate_with_real_model(source, mask_img, prompt)
            logger.info("Generated using real SDXL model")
        except Exception as exc:
            import traceback
            logger.error(
                "Real model failed — falling back to stub effect.\n"
                "Exception type : %s\n"
                "Exception msg  : %s\n"
                "Model path     : %s\n"
                "Traceback:\n%s",
                type(exc).__name__,
                exc,
                _MODEL_PATH,
                traceback.format_exc(),
            )
            prompt_lower = prompt.strip().lower()
            effect_fn = _PROMPT_EFFECTS.get(prompt_lower, _apply_generic_effect)
            result = effect_fn(source, mask_arr)

    _RESULT_DIR.mkdir(parents=True, exist_ok=True)
    result_path = _RESULT_DIR / f"result_{generation_id}.png"
    result.save(result_path)
    return result_path
