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
 * Creates (or reuses) a Roboflow annotation session for an uploaded image.
 * Returns { roboflow_image_id, annotate_url }.
 */
export async function createRoboflowSession(imageId) {
  const res = await fetch(`${BASE}/annotations/session?image_id=${encodeURIComponent(imageId)}`, {
    method: "POST",
  });

  const body = await res.json();
  if (!res.ok) {
    throw new Error(body.detail || "Could not start Roboflow annotation session.");
  }

  return body;
}

/**
 * Polls Roboflow (via the backend) for a finished annotation.
 * Returns { ready, mask_data, message } — mask_data is a data: URL when ready.
 */
export async function fetchRoboflowMask(imageId) {
  const res = await fetch(`${BASE}/annotations/mask/${encodeURIComponent(imageId)}`);

  const body = await res.json();
  if (!res.ok) {
    throw new Error(body.detail || "Could not fetch the Roboflow mask.");
  }

  return body;
}