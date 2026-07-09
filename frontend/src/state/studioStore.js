import { useState, useCallback } from "react";

export const STATUS = {
  IDLE: "idle",
  UPLOADED: "uploaded",
  ANNOTATING: "annotating",
  MASK_READY: "mask_ready",
  GENERATING: "generating",
  COMPLETE: "complete",
  FAILED: "failed",
};

/**
 * Single source of truth for the studio page.
 * KPI 1 only needs the shape of this state (so every panel has
 * something to render an empty/placeholder state against).
 * KPI 2/4 wire real upload data in, KPI 5/6 wire mask data in,
 * KPI 9 wires the generation result in.
 */
export function useStudioState() {
  const [image, setImage] = useState(null); // { id, file, name, size, previewUrl }
  const [mask, setMask] = useState(null); // { id, previewUrl }
  const [prompt, setPrompt] = useState("");
  const [status, setStatus] = useState(STATUS.IDLE);
  const [result, setResult] = useState(null); // { url }
  const [error, setError] = useState(null);

  const reset = useCallback(() => {
    setImage(null);
    setMask(null);
    setPrompt("");
    setStatus(STATUS.IDLE);
    setResult(null);
    setError(null);
  }, []);

  return {
    image, setImage,
    mask, setMask,
    prompt, setPrompt,
    status, setStatus,
    result, setResult,
    error, setError,
    reset,
  };
}