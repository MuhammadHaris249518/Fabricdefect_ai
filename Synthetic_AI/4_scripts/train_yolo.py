"""
STEP 4 - Train a YOLOv8-nano defect detector on your synthetic images,
and validate it against your real defect photos.

Run this AFTER auto_generate.py has produced images + labels, and after
you've manually annotated ../2_training_real/images/ into YOLO format in
../2_training_real/labels/ (using CVAT, LabelImg, or Roboflow, then
exporting as "YOLO" format).

WHY THIS FILE NEEDED A SMALL CHANGE:
  dataset.yaml's `path: ../` line is only unambiguous if YOLO resolves it
  relative to the yaml file's own folder - to remove any doubt, this
  script now regenerates dataset.yaml with a fully absolute path every
  time it runs, so training works the same regardless of where you
  launch this script from.
"""
import os
from ultralytics import YOLO


def main():
    scripts_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.abspath(os.path.join(scripts_dir, ".."))
    sandbox_dir = os.path.join(project_root, "6_yolo_sandbox")
    yaml_path = os.path.join(sandbox_dir, "dataset.yaml")

    os.makedirs(sandbox_dir, exist_ok=True)

    dataset_yaml_content = (
        f"path: {project_root}\n"
        f"train: 5_output_dataset/images\n"
        f"val: 2_training_real/images\n"
        f"names:\n"
        f"  0: hole\n"
        f"  1: oil_stain\n"
    )
    with open(yaml_path, "w") as f:
        f.write(dataset_yaml_content)
    print(f"Wrote dataset config with absolute path to: {yaml_path}")

    print("Initializing YOLOv8 Nano model...")
    model = YOLO("yolov8n.pt")  # auto-downloads pretrained nano weights on first run

    print("Training YOLO on synthetic data, validating on real data...")
    results = model.train(
        data=yaml_path,
        epochs=30,
        imgsz=512,
        batch=16,          # lower this (e.g. to 8) if you hit a CUDA out-of-memory error
        project=sandbox_dir,
        name="defect_experiment",
    )

    print("\nYOLO training complete.")
    print(f"Results, precision charts, and weights saved to: {os.path.join(sandbox_dir, 'defect_experiment')}")


if __name__ == "__main__":
    main()
