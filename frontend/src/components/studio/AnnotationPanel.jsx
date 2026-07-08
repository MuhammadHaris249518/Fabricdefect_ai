// Repo path: frontend/src/components/studio/AnnotationPanel.jsx  (REWRITTEN)
import { useState, useRef, useEffect, useCallback } from "react";
import { Lock, Loader2 } from "lucide-react";
import AnnotationCanvas from "./annotation/AnnotationCanvas";
import Toolbar from "./annotation/Toolbar";
import { useAnnotationHistory } from "../../hooks/useAnnotationHistory";
import { rasterizeMask, hasPaintedRegion } from "../../lib/annotation/maskEngine";
import { segmentWithSam } from "../../services/api";

const PANEL_HEIGHT = 360;

/**
 * Holds all per-image annotation state (tool, brush size, shape history,
 * natural image size). Mounted with key={image.id} by the parent so a new
 * upload gets a fresh instance — and therefore fresh state — for free,
 * instead of imperatively resetting state in an effect.
 */
function AnnotationWorkspace({ image, onMaskChange }) {
  const containerRef = useRef(null);
  const canvasRef = useRef(null);
  const [containerWidth, setContainerWidth] = useState(0);
  const [naturalSize, setNaturalSize] = useState({ width: 0, height: 0 });
  const [tool, setTool] = useState("brush");
  const [brushSize, setBrushSize] = useState(28);
  const [samLoading, setSamLoading] = useState(false);
  const [samError, setSamError] = useState(null);

  const { shapes, commit, undo, redo, canUndo, canRedo, reset } = useAnnotationHistory([]);

   // When the AI Select tool is used, call MobileSAM with the box the user dragged
   // and feed the returned mask into the same contract the rest of the
   // studio uses (dataUrl + previewUrl). This means Generate works unchanged.
   const handleSamBoxReady = useCallback(
     async (box) => {
       if (!image?.id) return;
       setSamLoading(true);
       setSamError(null);
       try {
         const { mask_data } = await segmentWithSam({ imageId: image.id, box });
         onMaskChange?.({ dataUrl: mask_data, previewUrl: mask_data });
       } catch (err) {
         setSamError(err.message || "AI segmentation failed.");
       } finally {
         setSamLoading(false);
       }
     },
     [image, onMaskChange]
   );

  useEffect(() => {
    const el = containerRef.current;
    if (!el) return undefined;
 
 
    const observer = new ResizeObserver((entries) => {
      setContainerWidth(entries[0].contentRect.width);
    });
    observer.observe(el);
    return () => observer.disconnect();
  }, []);

  const handleCommitShape = useCallback(
    (shape) => {
      const withId = { ...shape, id: `${Date.now()}-${Math.random().toString(36).slice(2, 8)}` };
      commit([...shapes, withId]);
    },
    [shapes, commit]
  );

  // Re-rasterize and hand the mask up whenever the committed shape history changes.
  useEffect(() => {
    if (!naturalSize.width || !naturalSize.height) return;

    if (shapes.length === 0) {
      onMaskChange?.(null);
      return;
    }

    const canvas = rasterizeMask(shapes, naturalSize.width, naturalSize.height);
    if (!hasPaintedRegion(canvas)) {
      onMaskChange?.(null);
      return;
    }

    const dataUrl = canvas.toDataURL("image/png");
    onMaskChange?.({ dataUrl, previewUrl: dataUrl });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [shapes, naturalSize]);

  return (
    <>
      <div
        ref={containerRef}
        className="relative flex items-center justify-center overflow-hidden rounded-card border border-dashed border-gray-300 bg-surface"
        style={{ minHeight: PANEL_HEIGHT }}
      >
        <AnnotationCanvas
          ref={canvasRef}
          imageUrl={image.previewUrl}
          tool={tool}
          brushSize={brushSize}
          shapes={shapes}
          onCommitShape={handleCommitShape}
          onSamBoxReady={handleSamBoxReady}
          containerSize={{ width: containerWidth, height: PANEL_HEIGHT }}
          onImageLoad={setNaturalSize}
        />
        {samLoading && (
          <div className="pointer-events-none absolute inset-0 flex items-center justify-center rounded-card bg-white/60">
            <span className="flex items-center gap-2 text-sm font-medium text-accent">
              <Loader2 className="h-4 w-4 animate-spin" /> AI is generating the mask…
            </span>
          </div>
        )}
      </div>

      <div className="mt-3">
        <Toolbar
          tool={tool}
          onToolChange={setTool}
          brushSize={brushSize}
          onBrushSizeChange={setBrushSize}
          onUndo={undo}
          onRedo={redo}
          canUndo={canUndo}
          canRedo={canRedo}
          onZoomIn={() => canvasRef.current?.zoomIn()}
          onZoomOut={() => canvasRef.current?.zoomOut()}
          onZoomReset={() => canvasRef.current?.resetView()}
          onClearAll={reset}
          hasShapes={shapes.length > 0}
        />
        {samError && (
          <p className="mt-2 text-xs font-medium text-alert">{samError}</p>
        )}
      </div>
    </>
  );
}

/**
 * FR-03/FR-04/FR-05 (KPI 5/6/7): in-house brush/eraser/rectangle/polygon
 * annotation tool. Produces a black/white PNG mask (white = editable
 * region) at the exact pixel dimensions of the uploaded image, handed to
 * the parent via onMaskChange — the same {dataUrl, previewUrl} contract
 * used everywhere else in the studio, regardless of which drawing engine
 * sits behind it.
 */
export default function AnnotationPanel({ image, mask, onMaskChange }) {
  return (
    <div className="rounded-card border border-gray-200 bg-white p-4 shadow-sm">
      <div className="mb-3 flex items-center justify-between">
        <h2 className="text-sm font-semibold text-text-primary">2. Annotate Region</h2>
        {mask && (
          <span className="flex items-center gap-1 rounded-full bg-success/10 px-2 py-0.5 text-xs font-medium text-success">
            Mask ready
          </span>
        )}
      </div>

      {!image ? (
        <div
          className="flex flex-col items-center justify-center gap-2 rounded-card border border-dashed border-gray-300 bg-surface p-6 text-center"
          style={{ minHeight: PANEL_HEIGHT }}
        >
          <Lock className="h-7 w-7 text-text-secondary" />
          <p className="text-sm font-medium text-text-primary">
            Upload an image to begin annotation
          </p>
          <p className="max-w-xs text-xs text-text-secondary">
            Paint, draw a rectangle, or trace a polygon over the region you want the AI to
            modify.
          </p>
        </div>
      ) : (
        <AnnotationWorkspace key={image.id} image={image} onMaskChange={onMaskChange} />
      )}
    </div>
  );
}