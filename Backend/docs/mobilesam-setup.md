# MobileSAM Setup

## Requirements

1. `pip install -r requirements.txt` (installs torch, torchvision, numpy, and mobile_sam from GitHub — requires network access to github.com during install)
2. `bash scripts/download_sam_weights.sh` — downloads the checkpoint into `app/ml/sam/weights/mobile_sam.pt` (gitignored, ~40MB)
3. Start the backend normally; the model loads lazily on the first `/api/v1/sam/segment` call, not at boot.

## Dependencies

The following dependencies are required and are specified in `requirements.txt`:

- `torch==2.4.1`
- `torchvision==0.19.1`
- `numpy==1.26.4`
- `mobile_sam` (installed from GitHub: https://github.com/ChaoningZhang/MobileSAM)

## Troubleshooting

### Model checkpoint not found

If you see an error about the checkpoint not being found, ensure you've run the download script:

```bash
bash scripts/download_sam_weights.sh
```

### Network policy preventing pip install

If your environment cannot reach GitHub via pip, you can vendor MobileSAM as a git submodule at `Backend/app/ml/sam/vendor/MobileSAM/` and add that path to `sys.path` in `predictor.py` rather than relying on pip.