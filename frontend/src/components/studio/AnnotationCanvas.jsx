// Repo path: frontend/src/components/studio/AnnotationCanvas.jsx  (NEW FILE)
import { useRef, useEffect, useState, useCallback } from "react";
import { Paintbrush, Hexagon, Eraser, RotateCcw, Undo2 } from "lucide-react";

const OVERLAY_COLOR = "rgba(214, 69, 69, 0.45)";
const DEFAULT_BRUSH = 28;

export default function AnnotationCanvas({ imageUrl, disabled, onMaskChange }) {
  const displayCanvasRef = useRef(null); // visible: image + red overlay
  const maskCanvasRef = useRef(null);    // hidden: black/white binary mask
  const imgRef = useRef(null);

  const [tool, setTool] = useState("brush");
  const [brushSize, setBrushSize] = useState(DEFAULT_BRUSH);
  const [isDrawing, setIsDrawing] = useState(false);
  const [polygonPoints, setPolygonPoints] = useState([]);
  const [strokes, setStrokes] = useState([]);
  const [naturalSize, setNaturalSize] = useState({ w: 0, h: 0 });

  // Load the image and size both canvases to its true resolution, so the
  // exported mask is pixel-accurate regardless of how small it's displayed.
  useEffect(() => {
    if (!imageUrl) return;
    const img = new Image();
    img.onload = () => {
      imgRef.current = img;
      setNaturalSize({ w: img.naturalWidth, h: img.naturalHeight });
      const display = displayCanvasRef.current;
      const mask = maskCanvasRef.current;
      if (display && mask) {
        display.width = img.naturalWidth;
        display.height = img.naturalHeight;
        mask.width = img.naturalWidth;
        mask.height = img.naturalHeight;
      }
      setStrokes([]);
      setPolygonPoints([]);
    };
    img.src = imageUrl;
  }, [imageUrl]);

  const paintStroke = (dctx, mctx, stroke) => {
    if (stroke.tool === "brush") {
      [
        [dctx, OVERLAY_COLOR],
        [mctx, "white"],
      ].forEach(([ctx, color]) => {
        ctx.save();
        ctx.strokeStyle = color;
        ctx.lineWidth = stroke.size;
        ctx.lineCap = "round";
        ctx.lineJoin = "round";
        ctx.beginPath();
        stroke.points.forEach(([x, y], i) => (i === 0 ? ctx.moveTo(x, y) : ctx.lineTo(x, y)));
        ctx.stroke();
        ctx.restore();
      });
    } else if (stroke.tool === "polygon" && stroke.points.length >= 3) {
      [
        [dctx, OVERLAY_COLOR],
        [mctx, "white"],
      ].forEach(([ctx, color]) => {
        ctx.save();
        ctx.fillStyle = color;
        ctx.beginPath();
        stroke.points.forEach(([x, y], i) => (i === 0 ? ctx.moveTo(x, y) : ctx.lineTo(x, y)));
        ctx.closePath();
        ctx.fill();
        ctx.restore();
      });
    }
  };

  const redraw = useCallback((strokeList, previewPoints) => {
    const display = displayCanvasRef.current;
    const mask = maskCanvasRef.current;
    const img = imgRef.current;
    if (!display || !mask || !img) return;

    const dctx = display.getContext("2d");
    const mctx = mask.getContext("2d");

    dctx.clearRect(0, 0, display.width, display.height);
    dctx.drawImage(img, 0, 0, display.width, display.height);

    mctx.fillStyle = "black";
    mctx.fillRect(0, 0, mask.width, mask.height);

    strokeList.forEach((s) => paintStroke(dctx, mctx, s));

    if (previewPoints && previewPoints.length > 0) {
      dctx.save();
      dctx.strokeStyle = "#D64545";
      dctx.fillStyle = "#D64545";
      dctx.lineWidth = 2;
      dctx.beginPath();
      previewPoints.forEach(([x, y], i) => (i === 0 ? dctx.moveTo(x, y) : dctx.lineTo(x, y)));
      dctx.stroke();
      previewPoints.forEach(([x, y]) => {
        dctx.beginPath();
        dctx.arc(x, y, 4, 0, Math.PI * 2);
        dctx.fill();
      });
      dctx.restore();
    }
  }, []);

  const emitMask = useCallback(
    (strokeList) => {
      const mask = maskCanvasRef.current;
      if (!mask) return;
      onMaskChange?.(strokeList.length > 0 ? mask.toDataURL("image/png") : null);
    },
    [onMaskChange]
  );

  useEffect(() => {
    if (!imgRef.current) return;
    redraw(strokes, polygonPoints);
    emitMask(strokes);
  }, [strokes, polygonPoints, redraw, emitMask]);

  const getCanvasCoords = (e) => {
    const canvas = displayCanvasRef.current;
    const rect = canvas.getBoundingClientRect();
    const scaleX = canvas.width / rect.width;
    const scaleY = canvas.height / rect.height;
    const clientX = e.touches ? e.touches[0].clientX : e.clientX;
    const clientY = e.touches ? e.touches[0].clientY : e.clientY;
    return [(clientX - rect.left) * scaleX, (clientY - rect.top) * scaleY];
  };

  const handlePointerDown = (e) => {
    if (disabled || !imgRef.current) return;
    const [x, y] = getCanvasCoords(e);
    if (tool === "brush") {
      setIsDrawing(true);
      setStrokes((prev) => [...prev, { tool: "brush", size: brushSize, points: [[x, y]] }]);
    } else {
      setPolygonPoints((prev) => [...prev, [x, y]]);
    }
  };

  const handlePointerMove = (e) => {
    if (disabled || tool !== "brush" || !isDrawing) return;
    const [x, y] = getCanvasCoords(e);
    setStrokes((prev) => {
      const next = [...prev];
      const last = { ...next[next.length - 1] };
      last.points = [...last.points, [x, y]];
      next[next.length - 1] = last;
      return next;
    });
  };

  const finishBrushStroke = () => setIsDrawing(false);

  const closePolygon = () => {
    if (polygonPoints.length >= 3) {
      setStrokes((prev) => [...prev, { tool: "polygon", points: polygonPoints }]);
    }
    setPolygonPoints([]);
  };

  const handleUndo = () => setStrokes((prev) => prev.slice(0, -1));
  const handleClear = () => {
    setStrokes([]);
    setPolygonPoints([]);
  };

  return (
    <div className="flex flex-col gap-3">
      <div
        className="relative w-full overflow-hidden rounded-card border border-dashed border-gray-300 bg-surface"
        style={{
          aspectRatio: naturalSize.w && naturalSize.h ? `${naturalSize.w} / ${naturalSize.h}` : "4 / 3",
        }}
      >
        <canvas
          ref={displayCanvasRef}
          className="absolute inset-0 h-full w-full cursor-crosshair touch-none"
          onMouseDown={handlePointerDown}
          onMouseMove={handlePointerMove}
          onMouseUp={finishBrushStroke}
          onMouseLeave={finishBrushStroke}
          onTouchStart={handlePointerDown}
          onTouchMove={handlePointerMove}
          onTouchEnd={finishBrushStroke}
          onDoubleClick={tool === "polygon" ? closePolygon : undefined}
        />
        <canvas ref={maskCanvasRef} className="hidden" />
      </div>

      <div className="flex flex-wrap items-center gap-2">
        <button
          type="button"
          onClick={() => setTool("brush")}
          className={`flex items-center gap-1 rounded-card border px-2.5 py-1.5 text-xs font-medium ${
            tool === "brush" ? "border-accent bg-accent/10 text-accent" : "border-gray-200 text-text-secondary"
          }`}
        >
          <Paintbrush className="h-3.5 w-3.5" /> Brush
        </button>
        <button
          type="button"
          onClick={() => setTool("polygon")}
          className={`flex items-center gap-1 rounded-card border px-2.5 py-1.5 text-xs font-medium ${
            tool === "polygon" ? "border-accent bg-accent/10 text-accent" : "border-gray-200 text-text-secondary"
          }`}
        >
          <Hexagon className="h-3.5 w-3.5" /> Polygon
        </button>

        {tool === "brush" && (
          <label className="flex items-center gap-2 text-xs text-text-secondary">
            Size
            <input
              type="range"
              min="8"
              max="80"
              value={brushSize}
              onChange={(e) => setBrushSize(Number(e.target.value))}
              className="w-24"
            />
          </label>
        )}

        {tool === "polygon" && polygonPoints.length > 0 && (
          <button
            type="button"
            onClick={closePolygon}
            className="rounded-card border border-accent px-2.5 py-1.5 text-xs font-medium text-accent"
          >
            Close shape ({polygonPoints.length} pts)
          </button>
        )}

        <div className="ml-auto flex gap-2">
          <button
            type="button"
            onClick={handleUndo}
            disabled={strokes.length === 0}
            className="flex items-center gap-1 rounded-card border border-gray-200 px-2.5 py-1.5 text-xs font-medium text-text-secondary disabled:cursor-not-allowed disabled:opacity-50"
          >
            <Undo2 className="h-3.5 w-3.5" /> Undo
          </button>
          <button
            type="button"
            onClick={handleClear}
            disabled={strokes.length === 0}
            className="flex items-center gap-1 rounded-card border border-gray-200 px-2.5 py-1.5 text-xs font-medium text-text-secondary disabled:cursor-not-allowed disabled:opacity-50"
          >
            <Eraser className="h-3.5 w-3.5" /> Clear
          </button>
          <button
            type="button"
            onClick={handleClear}
            disabled={strokes.length === 0}
            className="flex items-center gap-1 rounded-card border border-gray-200 px-2.5 py-1.5 text-xs font-medium text-text-secondary disabled:cursor-not-allowed disabled:opacity-50"
          >
            <RotateCcw className="h-3.5 w-3.5" /> Reset
          </button>
        </div>
      </div>
    </div>
  );
}