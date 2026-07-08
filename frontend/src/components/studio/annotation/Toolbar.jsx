// Repo path: frontend/src/components/studio/annotation/Toolbar.jsx  (NEW FILE)
import {
  Paintbrush2,
  Eraser,
  Square,
  Hexagon,
  Hand,
  Sparkles,
  Undo2,
  Redo2,
  ZoomIn,
  ZoomOut,
  Maximize2,
  Trash2,
} from "lucide-react";

const TOOLS = [
  { id: "sam", label: "AI Select", icon: Sparkles },
  { id: "brush", label: "Brush", icon: Paintbrush2 },
  { id: "eraser", label: "Eraser", icon: Eraser },
  { id: "rectangle", label: "Rectangle", icon: Square },
  { id: "polygon", label: "Polygon", icon: Hexagon },
  { id: "pan", label: "Pan", icon: Hand },
];

function IconButton({ title, onClick, disabled, active, children }) {
  return (
    <button
      type="button"
      title={title}
      onClick={onClick}
      disabled={disabled}
      className={`rounded-card border p-1.5 text-text-secondary transition-colors disabled:cursor-not-allowed disabled:opacity-40 ${
        active ? "border-accent bg-accent/5 text-accent" : "border-gray-200 hover:border-gray-300"
      }`}
    >
      {children}
    </button>
  );
}

export default function Toolbar({
  tool,
  onToolChange,
  brushSize,
  onBrushSizeChange,
  onUndo,
  onRedo,
  canUndo,
  canRedo,
  onZoomIn,
  onZoomOut,
  onZoomReset,
  onClearAll,
  hasShapes,
}) {
  return (
    <div className="flex flex-col gap-2">
      <div className="flex flex-wrap items-center gap-1.5">
        {TOOLS.map(({ id, label, icon: Icon }) => (
          <button
            key={id}
            type="button"
            title={label}
            onClick={() => onToolChange(id)}
            className={`flex items-center gap-1 rounded-card border px-2 py-1 text-xs font-medium transition-colors ${
              tool === id
                ? "border-accent bg-accent/5 text-accent"
                : "border-gray-200 text-text-secondary hover:border-gray-300"
            }`}
          >
            <Icon className="h-3.5 w-3.5" />
            {label}
          </button>
        ))}

        <div className="mx-1 h-5 w-px bg-gray-200" />

        <IconButton title="Undo" onClick={onUndo} disabled={!canUndo}>
          <Undo2 className="h-3.5 w-3.5" />
        </IconButton>
        <IconButton title="Redo" onClick={onRedo} disabled={!canRedo}>
          <Redo2 className="h-3.5 w-3.5" />
        </IconButton>

        <div className="mx-1 h-5 w-px bg-gray-200" />

        <IconButton title="Zoom in" onClick={onZoomIn}>
          <ZoomIn className="h-3.5 w-3.5" />
        </IconButton>
        <IconButton title="Zoom out" onClick={onZoomOut}>
          <ZoomOut className="h-3.5 w-3.5" />
        </IconButton>
        <IconButton title="Reset view" onClick={onZoomReset}>
          <Maximize2 className="h-3.5 w-3.5" />
        </IconButton>

        <button
          type="button"
          onClick={onClearAll}
          disabled={!hasShapes}
          className="ml-auto flex items-center gap-1 rounded-card border border-gray-200 px-2 py-1 text-xs font-medium text-text-secondary transition-colors hover:border-gray-300 disabled:cursor-not-allowed disabled:opacity-40"
        >
          <Trash2 className="h-3.5 w-3.5" /> Clear all
        </button>
      </div>

      {(tool === "brush" || tool === "eraser") && (
        <label className="flex items-center gap-2 text-xs text-text-secondary">
          Brush size
          <input
            type="range"
            min="4"
            max="100"
            value={brushSize}
            onChange={(e) => onBrushSizeChange(Number(e.target.value))}
            className="flex-1"
          />
          <span className="w-10 text-right tabular-nums">{brushSize}px</span>
        </label>
      )}

      {tool === "polygon" && (
        <p className="text-[11px] text-text-secondary">
          Click to place points. Click the first point again (or press Enter) to close the
          shape. Press Esc to cancel.
        </p>
      )}

      {tool === "pan" && (
        <p className="text-[11px] text-text-secondary">
          Drag to pan. Scroll to zoom from any tool.
        </p>
      )}

      {tool === "sam" && (
        <p className="text-[11px] text-text-secondary">
          Drag a rough box around the defect area. Release to let AI tighten it into a precise mask.
        </p>
      )}
    </div>
  );
}