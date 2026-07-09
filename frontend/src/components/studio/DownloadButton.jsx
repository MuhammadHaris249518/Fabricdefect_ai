import { Download } from "lucide-react";

export default function DownloadButton({ resultUrl, disabled }) {
  const handleDownload = () => {
    if (!resultUrl) return;
    const a = document.createElement("a");
    a.href = resultUrl;
    a.download = `crumblevision-generated-${Date.now()}.png`;
    document.body.appendChild(a);
    a.click();
    a.remove();
  };

  return (
    <button
      type="button"
      onClick={handleDownload}
      disabled={disabled}
      className="flex items-center gap-2 rounded-card border border-gray-200 bg-white px-4 py-2 text-sm font-medium text-text-primary hover:bg-surface disabled:cursor-not-allowed disabled:opacity-50"
    >
      <Download className="h-4 w-4" />
      Download High-Quality Image
    </button>
  );
}