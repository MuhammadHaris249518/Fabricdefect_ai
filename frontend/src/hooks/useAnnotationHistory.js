// Repo path: frontend/src/hooks/useAnnotationHistory.js  (NEW FILE)
import { useCallback, useState } from "react";

/**
 * Linear undo/redo history for the annotation shape list.
 *
 * `shapes` is always `history[index]` — the currently active state.
 * commit() truncates any redo-able future before pushing the new state,
 * matching standard editor undo/redo semantics (drawing after an undo
 * discards the redone branch).
 */
export function useAnnotationHistory(initialShapes = []) {
  const [history, setHistory] = useState([initialShapes]);
  const [index, setIndex] = useState(0);

  const commit = useCallback(
    (nextShapes) => {
      setHistory((prev) => [...prev.slice(0, index + 1), nextShapes]);
      setIndex((i) => i + 1);
    },
    [index]
  );

  const undo = useCallback(() => setIndex((i) => Math.max(0, i - 1)), []);

  const redo = useCallback(
    () => setIndex((i) => Math.min(history.length - 1, i + 1)),
    [history.length]
  );

  const reset = useCallback(() => {
    setHistory([[]]);
    setIndex(0);
  }, []);

  return {
    shapes: history[index],
    commit,
    undo,
    redo,
    reset,
    canUndo: index > 0,
    canRedo: index < history.length - 1,
  };
}