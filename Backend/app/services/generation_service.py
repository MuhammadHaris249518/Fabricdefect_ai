
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
from PIL import Image

logger = logging.getLogger(__name__)

_BACKEND_ROOT = Path(__file__).resolve().parent.parent
_RESULT_DIR = _BACKEND_ROOT / "storage" / "results"


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
    """
    Generate a defect image, constrained to the user's mask region.

    The mask (black/white PNG) defines the editable area:
      - White = region to modify
      - Black = protected, left unchanged

    Until Workstream B delivers the real model, this applies a synthetic
    effect matched to the prompt category. When the real model is ready,
    replace the body of this function with a call to the served model.
    """
    source = Image.open(source_path).convert("RGB")
    orig_size = source.size  # (width, height)

    mask_arr = _load_mask(mask_path, orig_size)

    if not mask_arr.any():
        logger.warning("Mask is empty, returning original image")
        result = source
    else:
        prompt_lower = prompt.strip().lower()
        effect_fn = _PROMPT_EFFECTS.get(prompt_lower, _apply_generic_effect)
        logger.info("Applying effect '%s' within mask region", prompt_lower)
        result = effect_fn(source, mask_arr)

    _RESULT_DIR.mkdir(parents=True, exist_ok=True)
    result_path = _RESULT_DIR / f"result_{generation_id}.png"
    result.save(result_path)
    return result_path
