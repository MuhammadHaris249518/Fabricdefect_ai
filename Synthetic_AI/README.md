# Crumbl Cookie defect detection - synthetic data pipeline

Generates synthetic cookie-defect images with a LoRA-fine-tuned Stable
Diffusion inpainting model, auto-labels them in YOLO format, and trains a
YOLOv8 detector - validated against a small set of real defect photos.

## One-time setup

```bash
cd 4_scripts
pip install -r requirements.txt --break-system-packages
python download_model.py
```

## What you need to add yourself (see the folder READMEs)

| Folder | What goes there |
|---|---|
| `1_input_data/clean_cookies/` | Clean, defect-free cookie photos |
| `1_input_data/cookie_masks/` | Same-named PNG masks: white = where a defect should be painted |
| `2_training_real/images/` | A handful of real defect photos, each with a matching `.txt` caption file |
| `2_training_real/labels/` | YOLO-format `.txt` labels for those same real photos (for validation) |

## Run order

```bash
cd 4_scripts
python train_lora.py      # teaches the model your specific defect look
python auto_generate.py   # generates + auto-labels synthetic defect images
python train_yolo.py      # trains + validates the YOLO detector
```

Results land in `6_yolo_sandbox/runs/defect_experiment/` (weights,
precision/recall curves, sample predictions).

## Folder map

```
1_input_data/        raw material for synthetic generation (clean photos + masks)
2_training_real/     your rare real defect photos (LoRA training + YOLO validation)
3_models/            the downloaded base model + your trained LoRA weights
4_scripts/           everything you run
5_output_dataset/    auto_generate.py's output: images/ + matching YOLO labels/
6_yolo_sandbox/      YOLO training config and results
```
