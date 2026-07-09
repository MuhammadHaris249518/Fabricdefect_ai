import torch
import matplotlib.pyplot as plt
import numpy as np
from PIL import Image
from mobile_sam import sam_model_registry, SamPredictor

# --- Step A: load the model once ---
device = "cuda" if torch.cuda.is_available() else "cpu"
print("Using device:", device)

model_type = "vit_t"                                   # "vit_t" = the tiny/mobile encoder
checkpoint = "MobileSAM/weights/mobile_sam.pt"

mobile_sam = sam_model_registry[model_type](checkpoint=checkpoint)
mobile_sam.to(device=device)
mobile_sam.eval()                                       # inference mode, not training

predictor = SamPredictor(mobile_sam)

# --- Step B: load your test photo ---
image = np.array(Image.open("test_images/cookie1.jpeg").convert("RGB"))
predictor.set_image(image)                              # runs the encoder ONCE per image

# --- Step C: click a point on the image to test segmentation ---
plt.imshow(image)
plt.title("Click the region you want to select, then close this window")
point = plt.ginput(1)[0]
plt.close()

input_point = np.array([[point[0], point[1]]])
input_label = np.array([1])                             # 1 = "this point is inside my target region"

# --- Step D: run the (fast) decoder to get a mask ---
masks, scores, _ = predictor.predict(
    point_coords=input_point,
    point_labels=input_label,
    multimask_output=True,                               # returns 3 candidate masks, ranked
)

best_mask = masks[np.argmax(scores)]                     # pick the highest-confidence one

# --- Step E: show the result ---
plt.imshow(image)
plt.imshow(best_mask, alpha=0.5, cmap="Reds")
plt.title(f"Best mask — confidence: {scores.max():.2f}")
plt.show()