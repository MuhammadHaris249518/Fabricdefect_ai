import { STATUS } from "../../state/studioStore";

const LABELS = {
  [STATUS.GENERATING]: "Generating your image…",
  [STATUS.COMPLETE]: "Generation complete",
  [STATUS.FAILED]: "Generation failed",
};

export default function ProgressIndicator({ status }) {
  const label = LABELS[status];

  if (!label) {
    return (
      <div className="rounded-card border border-dashed border-gray-200 bg-white px-4 py-3 text-center text-xs text-text-secondary">
        No generation in progress
      </div>
    );
  }

  const isFailed = status === STATUS.FAILED;
  const isComplete = status === STATUS.COMPLETE;

  return (
    <div className="rounded-card border border-gray-200 bg-white p-4 shadow-sm">
      <div className="mb-2 text-sm font-medium">
        <span className={isFailed ? "text-alert" : isComplete ? "text-success" : "text-text-primary"}>
          {label}
        </span>
      </div>
      <div className="h-2 w-full overflow-hidden rounded-full bg-surface">
        <div
          className={`h-full rounded-full transition-all ${
            isFailed
              ? "w-full bg-alert"
              : isComplete
              ? "w-full bg-success"
              : "w-2/3 animate-pulse bg-accent"
          }`}
        />
      </div>
    </div>
  );
}