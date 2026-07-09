"""
STEP 2 - Fine-tune a small LoRA adapter on your real (rare) defect photos.

NOTE ON SDXL: 
This script originally contained a simplified training loop for Stable Diffusion 1.5. 
Because `stable-diffusion-xl-1.0-inpainting-0.1` (SDXL) uses a much more complex 
architecture (two text encoders, pooled embeddings, micro-conditioning parameters), 
hand-rolling a training loop in a single file is highly error-prone and inefficient.

It is strongly recommended to use standard, community-supported tools for training SDXL LoRAs:
1. kohya_ss (GUI or CLI): Highly optimized, supports SDXL.
2. Hugging Face Diffusers (train_dreambooth_lora_sdxl.py): Official scripts.

If you use kohya_ss, point it to:
  - Model: ../3_models/stable-diffusion-xl-1.0-inpainting-0.1
  - Training Data: ../2_training_real/images
  - Output Name: cookie_defect_lora
  
Place the resulting `cookie_defect_lora.safetensors` in `../3_models/` so 
`auto_generate.py` can find it.
"""

import sys

def main():
    print("=========================================================================")
    print("SDXL LoRA Training Notice")
    print("=========================================================================")
    print("Training SDXL requires specialized scripts (like kohya_ss or Diffusers CLI)")
    print("due to its dual text encoders and complex conditioning requirements.")
    print("Please use an external tool to train your LoRA and save it as:")
    print("  3_models/cookie_defect_lora.safetensors")
    print("=========================================================================")
    print("See the comments in this file (train_lora.py) for more details.")
    sys.exit(0)

if __name__ == "__main__":
    main()
