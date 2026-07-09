"""
STEP 0 - Run this once, first, while you have internet access.
Downloads the stable-diffusion-xl-1.0-inpainting-0.1 checkpoint into
3_models/stable-diffusion-xl-1.0-inpainting-0.1/ so every later script can load it
with local_files_only=True and work fully offline.
"""
import os

# Disable symlinks (avoids Windows permission errors)
os.environ["HF_HUB_DISABLE_SYMLINKS"] = "1"
os.environ["HF_HUB_DISABLE_SYMLINKS_WARNING"] = "1"

import sys
from pathlib import Path
from huggingface_hub import snapshot_download, login
from huggingface_hub.utils import GatedRepoError, RepositoryNotFoundError


REPO_ID = "diffusers/stable-diffusion-xl-1.0-inpainting-0.1"


def download_and_save_locally():
    # Optional: Login if token is provided, though SDXL is not typically gated.
    hf_token = os.environ.get("HF_TOKEN")
    if hf_token:
        login(token=hf_token)

    script_dir = Path(__file__).resolve().parent
    target_dir = (script_dir / ".." / "3_models" / "stable-diffusion-xl-1.0-inpainting-0.1").resolve()

    # Idempotent: skip re-downloading if it's already there
    marker = target_dir / "model_index.json"
    if marker.exists():
        print(f"Model already present at {target_dir} - skipping download.")
        print("Delete that folder first if you want to re-download.")
        return

    target_dir.mkdir(parents=True, exist_ok=True)

    print(f"Connecting to Hugging Face Hub...")
    print(f"Repo : {REPO_ID}")
    print(f"Dest : {target_dir}")
    print("Downloading model — this will take a while. Progress shown below.")
    print("-" * 60)

    try:
        snapshot_download(
            repo_id=REPO_ID,
            local_dir=str(target_dir),   # download straight into target (no cache copy step)
            ignore_patterns=["*.msgpack", "*.h5", "flax_model*", "*.ckpt"],  # skip non-PyTorch weights
        )
    except RepositoryNotFoundError:
        print("\nError: Repository not found or token is invalid.")
        sys.exit(1)
    except KeyboardInterrupt:
        print("\nDownload interrupted by user.")
        sys.exit(1)
    except Exception as e:
        print(f"\nDownload failed: {e}")
        print("\nTroubleshooting tips:")
        print("  1. Make sure you are connected to the internet.")
        print("  2. Try again — partial downloads are resumed automatically.")
        sys.exit(1)

    print("-" * 60)
    print("Download complete!")
    print(f"Model saved to: {target_dir}")
    print("You can now safely disconnect from the internet.")


if __name__ == "__main__":
    download_and_save_locally()
