import { useState, useEffect, useCallback } from "react";
import { Lock, ExternalLink, RefreshCw, CheckCircle2, AlertCircle } from "lucide-react";
import { createRoboflowSession, fetchRoboflowMask } from "../../services/api";

/**
 * Roboflow-backed mask annotation panel (FR-03/FR-04/FR-05/FR-06, KPI 5/6).
 *
 * Roboflow doesn't ship an embeddable end-user annotation widget, so the
 * real flow is: upload the image into your Roboflow project, send the user
 * to Roboflow's own hosted Annotate page for that image, then poll Roboflow
 * for the finished annotation and convert it into a mask. An iframe is
 * attempted first for workspaces that allow framing; the "Open Roboflow
 * Annotator" link/button is the reliable fallback.
 */
export default function AnnotationPanel({ image, mask, onMaskChange }) {
  const [session, setSession] = useState(null); // { roboflow_image_id, annotate_url }
  const [starting, setStarting] = useState(false);
  const [checking, setChecking] = useState(false);
  const [iframeFailed, setIframeFailed] = useState(false);
  const [error, setError] = useState(null);

  useEffect(() => {
    setSession(null);
    setIframeFailed(false);
    setError(null);
  }, [image?.id]);

  const startSession = useCallback(async () => {
    if (!image?.id) return;
    setStarting(true);
    setError(null);
    try {
      const result = await createRoboflowSession(image.id);
      setSession(result);
    } catch (err) {
      setError(err.message || "Could not start the Roboflow annotation session.");
    } finally {
      setStarting(false);
    }
  }, [image]);

  const checkForMask = useCallback(async () => {
    if (!image?.id) return;
    setChecking(true);
    setError(null);
    try {
      const result = await fetchRoboflowMask(image.id);
      if (result.ready) {
        onMaskChange?.({ dataUrl: result.mask_data, previewUrl: result.mask_data });
      } else {
        setError(result.message || "Not annotated in Roboflow yet — finish drawing the mask, then check again.");
      }
    } catch (err) {
      setError(err.message || "Could not check Roboflow for the mask.");
    } finally {
      setChecking(false);
    }
  }, [image, onMaskChange]);

  const clearMask = () => onMaskChange?.(null);

  return (
    <div className="rounded-card border border-gray-200 bg-white p-4 shadow-sm">
      <div className="mb-3 flex items-center justify-between">
        <h2 className="text-sm font-semibold text-text-primary">2. Annotate Region (Roboflow)</h2>
        {mask && (
          <span className="flex items-center gap-1 rounded-full bg-success/10 px-2 py-0.5 text-xs font-medium text-success">
            <CheckCircle2 className="h-3 w-3" /> Mask ready
          </span>
        )}
      </div>

      {!image ? (
        <div className="flex min-h-[220px] flex-col items-center justify-center gap-2 rounded-card border border-dashed border-gray-300 bg-surface p-6 text-center">
          <Lock className="h-7 w-7 text-text-secondary" />
          <p className="text-sm font-medium text-text-primary">Upload an image to begin annotation</p>
          <p className="max-w-xs text-xs text-text-secondary">
            You'll annotate it in Roboflow, then bring the mask back here.
          </p>
        </div>
      ) : !session ? (
        <div className="flex min-h-[220px] flex-col items-center justify-center gap-3 rounded-card border border-dashed border-gray-300 bg-surface p-6 text-center">
          <p className="text-sm text-text-secondary">
            Ready to send this image to Roboflow for annotation.
          </p>
          <button
            type="button"
            onClick={startSession}
            disabled={starting || !image.id}
            className="rounded-card bg-accent px-4 py-2 text-sm font-semibold text-white disabled:cursor-wait disabled:opacity-60"
          >
            {starting ? "Uploading to Roboflow…" : "Start Roboflow Annotation"}
          </button>
        </div>
      ) : (
        <div className="flex flex-col gap-3">
          {!iframeFailed && (
            <iframe
              title="Roboflow Annotator"
              src={session.annotate_url}
              onError={() => setIframeFailed(true)}
              className="h-[420px] w-full rounded-card border border-gray-200"
            />
          )}
          <a          
            href={session.annotate_url}
            target="_blank"
            rel="noreferrer"
            className="flex items-center justify-center gap-2 rounded-card border border-gray-200 px-3 py-2 text-xs font-medium text-text-primary hover:bg-surface"
          >
            <ExternalLink className="h-3.5 w-3.5" /> Open Roboflow Annotator in a new tab
          </a>

          <p className="text-xs text-text-secondary">
            Draw the region to edit in Roboflow (white = editable area), save it there, then come back and check for the mask.
          </p>

          <div className="flex gap-2">
            <button
              type="button"
              onClick={checkForMask}
              disabled={checking}
              className="flex flex-1 items-center justify-center gap-1 rounded-card bg-accent px-3 py-2 text-xs font-semibold text-white disabled:cursor-wait disabled:opacity-60"
            >
              <RefreshCw className={`h-3.5 w-3.5 ${checking ? "animate-spin" : ""}`} />
              {checking ? "Checking Roboflow…" : "Check for Finished Mask"}
            </button>
            {mask && (
              <button
                type="button"
                onClick={clearMask}
                className="rounded-card border border-gray-200 px-3 py-2 text-xs font-medium text-text-secondary hover:bg-surface"
              >
                Clear
              </button>
            )}
          </div>

          {error && (
            <p className="flex items-start gap-1 text-xs text-alert">
              <AlertCircle className="mt-0.5 h-3.5 w-3.5 shrink-0" /> {error}
            </p>
          )}
        </div>
      )}
    </div>
  );
}