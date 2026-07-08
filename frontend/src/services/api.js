const BASE = "/api/v1";

/**
 * Uploads an image file to the backend and returns the persisted image metadata.
 * Returns { image_id, original_filename, content_type, size_bytes, created_at }.
 */
export async function uploadImage(file) {
  const formData = new FormData();
  formData.append("file", file);

  const res = await fetch(`${BASE}/images/upload`, {
    method: "POST",
    body: formData,
  });

  const body = await res.json();
  if (!res.ok) {
    throw new Error(body.detail || "Could not upload image.");
  }

  return body;
}

/**
 * Submits a generation request for an image, mask, and prompt.
 * Returns { id, image_id, prompt, status, result_url, error_message, created_at, updated_at }.
 */
export async function generateImage({ imageId, prompt, maskDataUrl }) {
  const res = await fetch(`${BASE}/generations`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      image_id: imageId,
      prompt,
      mask_data: maskDataUrl,
    }),
  });

  const body = await res.json();
  if (!res.ok) {
    throw new Error(body.detail || "Could not generate image.");
  }

  return body;
}

/**
 * Runs box-prompted MobileSAM for the user's rough rectangle selection.
 * `box` is [x0, y0, x1, y1] in image pixel coordinates; `point` is an
 * optional {x, y} disambiguation point inside the box.
 * Returns { mask_data } — a data: URL PNG mask (white = editable region).
 */
export async function segmentWithSam({ imageId, box, point }) {
  const res = await fetch(`${BASE}/sam/segment`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      image_id: imageId,
      box,
      ...(point ? { point } : {}),
    }),
  });

  const body = await res.json();
  if (!res.ok) {
    throw new Error(body.detail || "AI segmentation failed.");
  }
  return body;
}
