// Repo path: frontend/src/components/studio/annotation/AnnotationCanvas.jsx  (NEW FILE)
import {
  forwardRef,
  useImperativeHandle,
  useState,
  useEffect,
  useRef,
  useCallback,
  useMemo,
} from "react";
import { Stage, Layer, Image as KonvaImage, Line, Rect, Circle } from "react-konva";

const ZOOM_MIN = 0.4;
const ZOOM_MAX = 5;
const ZOOM_STEP = 1.2;
const CLOSE_VERTEX_THRESHOLD_PX = 12;

/**
 * Records every stroke/rect/polygon in *image pixel space* via Konva's
 * getRelativePointerPosition(), which already accounts for the stage's
 * zoom/pan transform. That means shapes can be handed straight to
 * maskEngine.rasterizeMask() with no further coordinate conversion,
 * regardless of what zoom level the user was drawing at.
 *
 * Exposes zoomIn/zoomOut/resetView imperatively so the parent's toolbar
 * can control zoom without duplicating pan/scale state.
 */
const AnnotationCanvas = forwardRef(function AnnotationCanvas(
   { imageUrl, tool, brushSize, shapes, onCommitShape, containerSize, onImageLoad, onSamBoxReady },
   ref
) {
   const [imgEl, setImgEl] = useState(null);
   const [naturalSize, setNaturalSize] = useState({ width: 0, height: 0 });
   const [scale, setScale] = useState(1);
   const [pos, setPos] = useState({ x: 0, y: 0 });
   const [draft, setDraft] = useState(null);
   const stageRef = useRef(null);
   const isDrawing = useRef(false);

  // Load the raw <img> element once per image URL.
  useEffect(() => {
    if (!imageUrl) return undefined;
    let cancelled = false;
    const img = new window.Image();
    img.onload = () => {
      if (cancelled) return;
      setImgEl(img);
      const size = { width: img.naturalWidth, height: img.naturalHeight };
      setNaturalSize(size);
      onImageLoad?.(size);
    };
    img.src = imageUrl;
    return () => {
      cancelled = true;
    };
    // onImageLoad intentionally excluded: identity may change per render in
    // the parent, and we only want this to re-run when the image itself changes.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [imageUrl]);

  const fitScale = useMemo(() => {
    if (!naturalSize.width || !containerSize?.width) return 1;
    const scaleX = containerSize.width / naturalSize.width;
    const scaleY = (containerSize.height || 360) / naturalSize.height;
    return Math.min(scaleX, scaleY, 1);
  }, [naturalSize, containerSize]);

  // Re-fit whenever a new image loads or the panel is resized.
  useEffect(() => {
    setScale(fitScale || 1);
    setPos({ x: 0, y: 0 });
  }, [fitScale, imageUrl]);

  useImperativeHandle(
    ref,
    () => ({
      zoomIn: () => setScale((s) => Math.min(ZOOM_MAX, s * ZOOM_STEP)),
      zoomOut: () => setScale((s) => Math.max(ZOOM_MIN, s / ZOOM_STEP)),
      resetView: () => {
        setScale(fitScale || 1);
        setPos({ x: 0, y: 0 });
      },
    }),
    [fitScale]
  );

  const getImagePoint = useCallback(() => {
    const stage = stageRef.current;
    if (!stage) return null;
    return stage.getRelativePointerPosition();
  }, []);

  const handleWheel = (e) => {
    e.evt.preventDefault();
    const stage = stageRef.current;
    const pointer = stage?.getPointerPosition();
    if (!pointer) return;

    const oldScale = scale;
    const mousePointTo = {
      x: (pointer.x - pos.x) / oldScale,
      y: (pointer.y - pos.y) / oldScale,
    };
    const direction = e.evt.deltaY > 0 ? -1 : 1;
    let newScale = direction > 0 ? oldScale / ZOOM_STEP : oldScale * ZOOM_STEP;
    newScale = Math.max(ZOOM_MIN, Math.min(ZOOM_MAX, newScale));

    setScale(newScale);
    setPos({
      x: pointer.x - mousePointTo.x * newScale,
      y: pointer.y - mousePointTo.y * newScale,
    });
  };

  const commitDraft = useCallback(
    (shapeToCommit) => {
      const shape = shapeToCommit || draft;
      if (!shape) return;

      if (shape.kind === "rect") {
        const normalized = {
          kind: "rect",
          erase: shape.erase,
          x: Math.min(shape.x, shape.x + shape.width),
          y: Math.min(shape.y, shape.y + shape.height),
          width: Math.abs(shape.width),
          height: Math.abs(shape.height),
        };
        if (normalized.width < 4 || normalized.height < 4) {
          setDraft(null);
          return;
        }
        onCommitShape(normalized);
      } else if (shape.kind === "stroke") {
        if (shape.points.length < 4) {
          setDraft(null);
          return;
        }
        onCommitShape(shape);
      } else if (shape.kind === "polygon") {
        if (shape.points.length < 6) {
          setDraft(null);
          return;
        }
        onCommitShape(shape);
      }
      setDraft(null);
    },
    [draft, onCommitShape]
  );

  const handleMouseDown = () => {
    if (tool === "pan") return;
    const point = getImagePoint();
    if (!point) return;

    if (tool === "sam") {
      isDrawing.current = true;
      setDraft({ kind: "rect", erase: false, sam: true, x: point.x, y: point.y, width: 0, height: 0 });
    } else if (tool === "brush" || tool === "eraser") {
      isDrawing.current = true;
      setDraft({
        kind: "stroke",
        erase: tool === "eraser",
        strokeWidth: brushSize,
        points: [point.x, point.y],
      });
    } else if (tool === "rectangle") {
      isDrawing.current = true;
      setDraft({ kind: "rect", erase: false, x: point.x, y: point.y, width: 0, height: 0 });
    } else if (tool === "polygon") {
      setDraft((prev) => {
        if (!prev || prev.kind !== "polygon") {
          return { kind: "polygon", erase: false, points: [point.x, point.y] };
        }
        const [firstX, firstY] = prev.points;
        const dist = Math.hypot(point.x - firstX, point.y - firstY);
        if (prev.points.length >= 6 && dist < CLOSE_VERTEX_THRESHOLD_PX / scale) {
          commitDraft(prev);
          return null;
        }
        return { ...prev, points: [...prev.points, point.x, point.y] };
      });
    }
  };

  const handleMouseMove = () => {
    if (tool === "pan") return;
    const point = getImagePoint();
    if (!point) return;

    if ((tool === "brush" || tool === "eraser") && isDrawing.current) {
      setDraft((prev) => (prev ? { ...prev, points: [...prev.points, point.x, point.y] } : prev));
    } else if ((tool === "rectangle" || tool === "sam") && isDrawing.current) {
      setDraft((prev) =>
        prev ? { ...prev, width: point.x - prev.x, height: point.y - prev.y } : prev
      );
    }
  };

  const handleMouseUp = () => {
    if (tool === "pan" || tool === "polygon") return; // polygon commits on vertex click, not release
    if (!isDrawing.current) return;
    isDrawing.current = false;

    if (tool === "sam" && draft?.kind === "rect") {
      const x0 = Math.min(draft.x, draft.x + draft.width);
      const y0 = Math.min(draft.y, draft.y + draft.height);
      const x1 = Math.max(draft.x, draft.x + draft.width);
      const y1 = Math.max(draft.y, draft.y + draft.height);
      if (x1 - x0 >= 8 && y1 - y0 >= 8) {
        onSamBoxReady?.([Math.round(x0), Math.round(y0), Math.round(x1), Math.round(y1)]);
      }
      setDraft(null);
      return;
    }

    commitDraft();
  };

  // Escape cancels an in-progress polygon; Enter closes it early.
  useEffect(() => {
    const onKey = (e) => {
      if (e.key === "Escape") setDraft(null);
      if (e.key === "Enter" && draft?.kind === "polygon") commitDraft(draft);
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [draft, commitDraft]);

  const renderShape = (shape, key) => {
    const fill = "rgba(42, 111, 219, 0.55)";
    const compositeProps = shape.erase ? { globalCompositeOperation: "destination-out" } : {};

    if (shape.kind === "stroke") {
      return (
        <Line
          key={key}
          points={shape.points}
          stroke={fill}
          strokeWidth={shape.strokeWidth}
          lineCap="round"
          lineJoin="round"
          {...compositeProps}
        />
      );
    }
    if (shape.kind === "rect") {
      return (
        <Rect
          key={key}
          x={shape.x}
          y={shape.y}
          width={shape.width}
          height={shape.height}
          fill={fill}
          {...compositeProps}
        />
      );
    }
    if (shape.kind === "polygon") {
      return (
        <Line
          key={key}
          points={shape.points}
          closed={shape.points.length >= 6}
          fill={fill}
          stroke={fill}
          strokeWidth={2}
          {...compositeProps}
        />
      );
    }
    return null;
  };

  if (!imageUrl || !containerSize?.width) return null;

  return (
    <Stage
      ref={stageRef}
      width={containerSize.width}
      height={containerSize.height || 360}
      scaleX={scale}
      scaleY={scale}
      x={pos.x}
      y={pos.y}
      draggable={tool === "pan"}
      onWheel={handleWheel}
      onMouseDown={handleMouseDown}
      onMouseMove={handleMouseMove}
      onMouseUp={handleMouseUp}
      onTouchStart={handleMouseDown}
      onTouchMove={handleMouseMove}
      onTouchEnd={handleMouseUp}
      onDragEnd={(e) => setPos({ x: e.target.x(), y: e.target.y() })}
      style={{ cursor: tool === "pan" ? "grab" : "crosshair" }}
    >
      <Layer listening={false}>
        {imgEl && (
          <KonvaImage image={imgEl} width={naturalSize.width} height={naturalSize.height} />
        )}
      </Layer>
      <Layer>
        {shapes.map((shape, i) => renderShape(shape, shape.id || i))}
        {draft && renderShape(draft, "draft")}
        {draft?.kind === "polygon" &&
          Array.from({ length: draft.points.length / 2 }).map((_, i) => (
            <Circle
              key={`vertex-${i}`}
              x={draft.points[i * 2]}
              y={draft.points[i * 2 + 1]}
              radius={4 / scale}
              fill="#2A6FDB"
            />
          ))}
      </Layer>
    </Stage>
  );
});

export default AnnotationCanvas;