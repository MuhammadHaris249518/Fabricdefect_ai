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