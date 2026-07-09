#!/usr/bin/env bash
# Downloads the MobileSAM checkpoint into app/ml/sam/weights/, separate
# from ai_experiments/ so the production code path never depends on the
# experiment folder.
set -euo pipefail

WEIGHTS_DIR="$(dirname "$0")/../app/ml/sam/weights"
CHECKPOINT_URL="https://github.com/ChaoningZhang/MobileSAM/raw/master/weights/mobile_sam.pt"
CHECKPOINT_PATH="${WEIGHTS_DIR}/mobile_sam.pt"

mkdir -p "${WEIGHTS_DIR}"

if [ -f "${CHECKPOINT_PATH}" ]; then
  echo "MobileSAM checkpoint already present at ${CHECKPOINT_PATH}"
  exit 0
fi

echo "Downloading MobileSAM checkpoint to ${CHECKPOINT_PATH} ..."
curl -L -o "${CHECKPOINT_PATH}" "${CHECKPOINT_URL}"
echo "Done."