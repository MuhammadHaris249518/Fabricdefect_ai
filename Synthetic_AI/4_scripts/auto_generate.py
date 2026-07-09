"""
STEP 3 - Generate synthetic defect images by inpainting your fine-tuned
defect concept onto clean cookie photos, using your hand-drawn masks to
control exactly where the defect appears - and automatically write a
matching YOLO-format label for every image produced.
"""
import os
import json
from pathlib import Path
from PIL import Image, ImageFilter
import torch
from diffusers import StableDiffusionXLInpaintPipeline

SCRIPT_DIR = Path(__file__).resolve().parent
ROOT_DIR   = SCRIPT_DIR.parent

CLASS_MAP = {"burnt_edges": 0, "crack": 1}

IMAGE_DEFECT_MAP = {
    "img_1": "burnt_edges",
    "img_2": "crack",
}

def mask_to_yolo_bbox(mask_image, class_id):
    """Compute a YOLO-format label line from a binary mask."""
    gray = mask_image.convert("L")
    bbox = gray.getbbox()
    if bbox is None:
        return None
    width, height = gray.size
    left, upper, right, lower = bbox
    x_center = (left + right) / 2 / width
    y_center = (upper + lower) / 2 / height
    box_w = (right - left) / width
    box_h = (lower - upper) / height
    return f"{class_id} {x_center:.6f} {y_center:.6f} {box_w:.6f} {box_h:.6f}"


def main():
    model_path    = ROOT_DIR / "3_models" / "stable-diffusion-xl-1.0-inpainting-0.1"
    lora_path     = ROOT_DIR / "3_models"
    lora_filename = "cookie_defect_lora.safetensors"
    clean_dir     = ROOT_DIR / "1_input_data" / "clean_cookies"
    mask_dir      = ROOT_DIR / "1_input_data" / "cookie_masks"
    images_out_dir = ROOT_DIR / "5_output_dataset" / "images"
    labels_out_dir = ROOT_DIR / "5_output_dataset" / "labels"
    metadata_file  = ROOT_DIR / "5_output_dataset" / "generation_metadata.json"

    images_out_dir.mkdir(parents=True, exist_ok=True)
    labels_out_dir.mkdir(parents=True, exist_ok=True)

    if torch.cuda.is_available():
        device = "cuda"
        dtype  = torch.float16
        print(f"GPU detected: {torch.cuda.get_device_name(0)}")
    else:
        device = "cpu"
        dtype  = torch.float32
        print("WARNING: Running on CPU will be very slow.")

    print("Loading local AI model (stable-diffusion-xl-1.0-inpainting-0.1)...")
    
    pipe = StableDiffusionXLInpaintPipeline.from_pretrained(
        str(model_path),
        torch_dtype=dtype,
        local_files_only=True,
    )
    
    if device == "cuda":
        pipe.enable_model_cpu_offload()

    pipe.enable_attention_slicing()
    pipe.enable_vae_slicing()  # Added: Prevents VRAM OOM when decoding 1024x1024 on 16GB Colab GPUs

    lora_full_path = lora_path / lora_filename
    if lora_full_path.exists():
        pipe.load_lora_weights(str(lora_path), weight_name=lora_filename)
        print(f"Loaded fine-tuned LoRA weights from {lora_filename}.")
    else:
        print("No trained LoRA found - generating with the base model only.")

    prompts_file = ROOT_DIR / "1_input_data" / "prompts.json"
    if not prompts_file.exists():
        print(f"Error: {prompts_file} not found.")
        return
    with open(prompts_file, "r") as f:
        defect_prompts = json.load(f)

    clean_filenames = [f for f in clean_dir.iterdir() if f.suffix.lower() in ('.png', '.jpg', '.jpeg')]
    if len(clean_filenames) == 0:
        print(f"No clean images found in {clean_dir}.")
        return

    generated_metadata = []
    global_counter = 0
    num_variants_per_prompt = 1  

    print(f"Starting generation loop at native SDXL resolution...")

    for filepath in clean_filenames:
        base_name    = filepath.stem
        mask_path    = mask_dir / f"{base_name}.png"

        if not mask_path.exists():
            continue

        assigned_defect = IMAGE_DEFECT_MAP.get(base_name)
        if assigned_defect is None or assigned_defect not in defect_prompts:
            continue

        # FIX: Upgrade scaling target to 1024x1024 for pristine SDXL textures
        init_image = Image.open(filepath).convert("RGB").resize((1024, 1024))

        mask_gray = Image.open(mask_path).convert("L").resize((1024, 1024))
        mask_array = [255 if px > 20 else 0 for px in mask_gray.getdata()]
        mask_image = Image.new("L", mask_gray.size)
        mask_image.putdata(mask_array)
        
        # Feather the mask so the generated defect blends seamlessly into the cookie
        mask_image = mask_image.filter(ImageFilter.GaussianBlur(radius=12))

        defect_type = assigned_defect
        class_id   = CLASS_MAP[defect_type]
        prompt_list = defect_prompts[defect_type]
        label_line = mask_to_yolo_bbox(mask_image, class_id)
        if label_line is None:
            continue

        for prompt in prompt_list:
            for v in range(num_variants_per_prompt):
                    global_counter += 1
                    out_stem       = f"synthetic_{defect_type}_{global_counter:04d}"
                    out_image_path = images_out_dir / f"{out_stem}.png"
                    out_label_path = labels_out_dir / f"{out_stem}.txt"

                    # Add a strong negative prompt to enforce photo realism
                    negative_prompt = "blurry, smooth, plastic texture, cartoon, drawing, 3d render"

                    output = pipe(
                        prompt=prompt,
                        negative_prompt=negative_prompt,
                        image=init_image,
                        mask_image=mask_image,
                        height=1024,      # FIX: Target Native Resolution
                        width=1024,       # FIX: Target Native Resolution
                        strength=0.95,    # High strength to fully replace the area, relying on feathering for blending
                        guidance_scale=7.0, # 7.0 is often the sweet spot for SDXL photorealism
                        num_inference_steps=40, 
                    ).images[0]

                    output.save(str(out_image_path))
                    with open(out_label_path, "w") as f:
                        f.write(label_line + "\n")

                    generated_metadata.append({
                        "image_name": f"{out_stem}.png",
                        "defect_class": defect_type,
                        "source_image": filepath.name,
                        "source_mask": mask_path.name,
                        "prompt_used": prompt,
                        "yolo_label": label_line,
                    })
                    print(f"  [{global_counter:04d}] {out_stem}.png exported.")

    with open(metadata_file, "w") as f:
        json.dump(generated_metadata, f, indent=4)

    print(f"Dataset creation complete!")


if __name__ == "__main__":
    main()