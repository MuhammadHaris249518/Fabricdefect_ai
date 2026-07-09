import { ImageOff } from "lucide-react";

function ImageSlot({ label, url, emptyText }) {
  return (
    <div className="flex-1">
      <p className="mb-2 text-xs font-semibold uppercase tracking-wide text-text-secondary">
        {label}
      </p>
      <div className="flex aspect-square w-full items-center justify-center overflow-hidden rounded-card border border-gray-200 bg-surface">
        {url ? (
          <img src={url} alt={label} className="h-full w-full object-cover" />
        ) : (
          <div className="flex flex-col items-center gap-2 text-text-secondary">
            <ImageOff className="h-6 w-6" />
            <p className="text-xs">{emptyText}</p>
          </div>
        )}
      </div>
    </div>
  );
}

export default function ComparisonView({ originalUrl, resultUrl }) {
  return (
    <div className="rounded-card border border-gray-200 bg-white p-4 shadow-sm">
      <h2 className="mb-3 text-sm font-semibold text-text-primary">4. Compare Result</h2>
      <div className="flex flex-col gap-4 sm:flex-row">
        <ImageSlot label="Original" url={originalUrl} emptyText="No image uploaded yet" />
        <ImageSlot label="Generated" url={resultUrl} emptyText="Your generated result will appear here" />
      </div>
    </div>
  );
}