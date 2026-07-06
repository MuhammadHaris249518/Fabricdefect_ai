// Repo path: frontend/src/components/studio/AnnotationPanel.jsx  (UPDATED — full replacement)
import { useCallback, useEffect, useRef, useState } from "react";
import { Lock, CloudUpload, CloudOff, Loader2 } from "lucide-react";
import AnnotationCanvas from "./AnnotationCanvas";
import { saveAnnotationMask } from "../../services/api";

const SYNC_DEBOUNCE_MS = 800;

export default function AnnotationPanel({ image, onMaskChange }) {
  const [syncState, setSyncState] = useState("idle"); // idle | saving | synced | roboflow_failed | error
  const debounceRef = useRef(null);
  const latestMaskRef = useRef(null);

  const handleMaskChange = useCallback(
    (maskDataUrl) => {
      latestMaskRef.current = maskDataUrl;
      onMaskChange(maskDataUrl ? { dataUrl: maskDataUrl } : null);

      if (!image?.id) return;
      if (!maskDataUrl) {
        setSyncState("idle");
        return;
      }

      if (debounceRef.current) clearTimeout(debounceRef.current);
      debounceRef.current = setTimeout(async () => {
        setSyncState("saving");
        try {
          const result = await saveAnnotationMask(image.id, latestMaskRef.current);
          setSyncState(result.roboflow_status === "synced" ? "synced" : "roboflow_failed");
        } catch {
          setSyncState("error");
        }
      }, SYNC_DEBOUNCE_MS);
    },
    [image, onMaskChange]
  );

  useEffect(() => () => debounceRef.current && clearTimeout(debounceRef.current), []);

  return (
    <div className="rounded-card border border-gray-200 bg-white p-4 shadow-sm">
      <div className="mb-3 flex items-center justify-between">
        <h2 className="text-sm font-semibold text-text-primary">2. Annotate Region</h2>
        <SyncBadge state={syncState} />
      </div>

      {!image ? (
        <div className="flex min-h-[220px] flex-col items-center justify-center gap-2 rounded-card border border-dashed border-gray-300 bg-surface text-center">
          <Lock className="h-7 w-7 text-text-secondary" />
          <p className="text-sm font-medium text-text-primary">Upload an image to begin annotation</p>
          <p className="max-w-xs text-xs text-text-secondary">
            Once uploaded, paint or outline the region you want the AI to modify.
          </p>
        </div>
      ) : (
        <AnnotationCanvas imageUrl={image.previewUrl} disabled={!image.id} onMaskChange={handleMaskChange} />
      )}
    </div>
  );
}

function SyncBadge({ state }) {
  const map = {
    idle: null,
    saving: { icon: Loader2, text: "Saving…", cls: "text-amber-500", spin: true },
    synced: { icon: CloudUpload, text: "Synced to Roboflow", cls: "text-success" },
    roboflow_failed: { icon: CloudOff, text: "Saved locally (Roboflow sync failed)", cls: "text-amber-500" },
    error: { icon: CloudOff, text: "Save failed", cls: "text-alert" },
  };
  const cfg = map[state];
  if (!cfg) return null;
  const Icon = cfg.icon;
  return (
    <span className={`flex items-center gap-1 text-xs font-medium ${cfg.cls}`}>
      <Icon className={`h-3.5 w-3.5 ${cfg.spin ? "animate-spin" : ""}`} /> {cfg.text}
    </span>
  );
}