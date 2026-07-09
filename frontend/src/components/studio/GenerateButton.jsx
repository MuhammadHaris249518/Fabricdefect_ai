import { Sparkles, Loader2 } from "lucide-react";
import { STATUS } from "../../state/studioStore";

export default function GenerateButton({ disabled, status, onClick }) {
  const isGenerating = status === STATUS.GENERATING;

  return (
    <button
      type="button"
      onClick={onClick}
      disabled={disabled}
      className="flex w-full items-center justify-center gap-2 rounded-card bg-accent px-4 py-3 text-sm font-semibold text-white transition-opacity hover:opacity-90 disabled:cursor-not-allowed disabled:bg-gray-300 disabled:text-text-secondary"
    >
      {isGenerating ? (
        <>
          <Loader2 className="h-4 w-4 animate-spin" />
          Generating…
        </>
      ) : (
        <>
          <Sparkles className="h-4 w-4" />
          Generate
        </>
      )}
    </button>
  );
}