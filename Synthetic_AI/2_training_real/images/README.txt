Put your real (rare) defect photos here - even 20-50 images is enough
to start. For each image, add a matching .txt file with the same base
filename containing a short caption, always including the same trigger
phrase, e.g.:

  cookie_defect_003.jpg
  cookie_defect_003.txt  ->  "a photo of cookie with [my_cookie_defect_v1]
                               hole defect, frayed edges, close-up"

That trigger phrase is what train_lora.py teaches the model to associate
with your defect's visual style, and it's the same phrase used in
auto_generate.py's prompts later. If you skip the .txt file, a generic
fallback caption is used instead, but real per-image captions work
better.

These images are also used as the validation set in dataset.yaml, so the
detector gets tested against real defects, not just synthetic ones.
