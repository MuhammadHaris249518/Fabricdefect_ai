#!/usr/bin/env python3
"""
Cross-platform downloader for the MobileSAM checkpoint.

Usage:
    python scripts/download_sam_weights.py

Run from anywhere — the path is resolved relative to this script's location,
not the current working directory.
"""
import sys
import urllib.request
from pathlib import Path

CHECKPOINT_URL = "https://github.com/ChaoningZhang/MobileSAM/raw/master/weights/mobile_sam.pt"
MIN_EXPECTED_BYTES = 35_000_000  # real file is ~38-40MB; anything smaller means a bad/partial download

WEIGHTS_DIR = Path(__file__).resolve().parent.parent / "app" / "ml" / "sam" / "weights"
CHECKPOINT_PATH = WEIGHTS_DIR / "mobile_sam.pt"


def _download_with_progress(url: str, dest: Path) -> None:
    def _report(block_num, block_size, total_size):
        if total_size <= 0:
            return
        downloaded = block_num * block_size
        pct = min(100, downloaded * 100 // total_size)
        sys.stdout.write(f"\r  {pct:3d}%  ({downloaded/1e6:.1f} MB / {total_size/1e6:.1f} MB)")
        sys.stdout.flush()

    urllib.request.urlretrieve(url, dest, reporthook=_report)
    print()  # newline after progress bar


def main() -> int:
    WEIGHTS_DIR.mkdir(parents=True, exist_ok=True)

    if CHECKPOINT_PATH.exists():
        size = CHECKPOINT_PATH.stat().st_size
        if size >= MIN_EXPECTED_BYTES:
            print(f"Checkpoint already present and looks valid: {CHECKPOINT_PATH} ({size/1e6:.1f} MB)")
            return 0
        else:
            print(f"Existing file at {CHECKPOINT_PATH} is only {size} bytes — "
                  f"looks like a corrupted/partial download. Re-downloading.")
            CHECKPOINT_PATH.unlink()

    print(f"Downloading MobileSAM checkpoint to {CHECKPOINT_PATH} ...")
    try:
        _download_with_progress(CHECKPOINT_URL, CHECKPOINT_PATH)
    except Exception as exc:
        print(f"ERROR: download failed: {exc}", file=sys.stderr)
        print("See Section 8 of MobileSAM_Checkpoint_Fix_Plan.md for troubleshooting "
              "(proxy/SSL issues, manual browser download fallback).", file=sys.stderr)
        return 1

    final_size = CHECKPOINT_PATH.stat().st_size
    if final_size < MIN_EXPECTED_BYTES:
        print(f"ERROR: downloaded file is only {final_size} bytes — expected ~38-40MB. "
              f"GitHub likely returned an error page instead of the binary. "
              f"Deleting bad file.", file=sys.stderr)
        CHECKPOINT_PATH.unlink()
        return 1

    print(f"Done. {CHECKPOINT_PATH} ({final_size/1e6:.1f} MB)")
    return 0


if __name__ == "__main__":
    sys.exit(main())