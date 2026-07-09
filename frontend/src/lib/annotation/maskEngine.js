// Repo path: frontend/src/lib/annotation/maskEngine.js  (NEW FILE)
/**
 * Pure, framework-agnostic rasterizer: turns the committed shape history
 * from AnnotationCanvas.jsx (brush strokes, rectangles, polygons, and
 * their eraser variants) into a single black/white mask canvas.
 *
 * No AI model involved — this is a direct, deterministic rasterization of
 * exactly what the user drew, at the image's natural pixel dimensions.
 *
 * Mask contract (matches generation_service.py's _load_mask() on the
 * backend — do not invert this without also updating the backend):
 *   white (255) = region to edit
 *   black (0)   = protected / unchanged
 *
 * Shape shapes come from AnnotationCanvas.jsx's commitDraft():
 *   { kind: "stroke",  erase, strokeWidth, points: [x1,y1,x2,y2,...] }  // brush / eraser
 *   { kind: "rect",    erase, x, y, width, height }                     // rectangle
 *   { kind: "polygon", erase, points: [x1,y1,x2,y2,...] }               // polygon
 *
 * Note: the "sam" (AI Select) tool never reaches this file — it bypasses
 * shape history entirely and calls the backend directly via
 * segmentWithSam() in AnnotationPanel.jsx. This file only ever sees
 * brush/eraser/rectangle/polygon shapes.
 */

export function rasterizeMask(shapes, width, height) {
  const canvas = document.createElement("canvas");
  canvas.width = width;
  canvas.height = height;
  const ctx = canvas.getContext("2d");

  // Start fully black (nothing selected).
  ctx.fillStyle = "#000000";
  ctx.fillRect(0, 0, width, height);

  ctx.fillStyle = "#ffffff";
  ctx.strokeStyle = "#ffffff";
  ctx.lineCap = "round";
  ctx.lineJoin = "round";

  for (const shape of shapes) {
    ctx.globalCompositeOperation = shape.erase ? "destination-out" : "source-over";

    if (shape.kind === "stroke") {
      drawStroke(ctx, shape);
    } else if (shape.kind === "rect") {
      drawRect(ctx, shape);
    } else if (shape.kind === "polygon") {
      drawPolygon(ctx, shape);
    }
  }

  // Erasing (destination-out) leaves transparent pixels, not black ones.
  // Flatten any transparency back to solid black so the exported PNG is a
  // clean two-tone black/white image with no alpha channel ambiguity when
  // the backend decodes it.
  ctx.globalCompositeOperation = "destination-over";
  ctx.fillStyle = "#000000";
  ctx.fillRect(0, 0, width, height);
  ctx.globalCompositeOperation = "source-over";

  return canvas;
}

function drawStroke(ctx, shape) {
  const { points, strokeWidth } = shape;
  if (points.length < 2) return;

  ctx.lineWidth = strokeWidth;
  ctx.beginPath();
  ctx.moveTo(points[0], points[1]);
  for (let i = 2; i < points.length; i += 2) {
    ctx.lineTo(points[i], points[i + 1]);
  }
  ctx.stroke();

  // A single click with no drag movement produces one point and no visible
  // stroke — paint a dot so a tap still marks something.
  if (points.length === 2) {
    ctx.beginPath();
    ctx.arc(points[0], points[1], strokeWidth / 2, 0, Math.PI * 2);
    ctx.fill();
  }
}

function drawRect(ctx, shape) {
  ctx.fillRect(shape.x, shape.y, shape.width, shape.height);
}

function drawPolygon(ctx, shape) {
  const { points } = shape;
  if (points.length < 6) return;

  ctx.beginPath();
  ctx.moveTo(points[0], points[1]);
  for (let i = 2; i < points.length; i += 2) {
    ctx.lineTo(points[i], points[i + 1]);
  }
  ctx.closePath();
  ctx.fill();
}

/**
 * True if the mask canvas has at least one painted (non-black) pixel.
 * AnnotationPanel.jsx uses this to avoid treating an all-black (nothing
 * drawn yet, or fully erased back to nothing) canvas as a "ready" mask.
 */
export function hasPaintedRegion(canvas) {
  const ctx = canvas.getContext("2d");
  const { width, height } = canvas;
  const { data } = ctx.getImageData(0, 0, width, height);

  for (let i = 0; i < data.length; i += 4) {
    if (data[i] > 10) return true; // R channel — anything above near-black
  }
  return false;
}