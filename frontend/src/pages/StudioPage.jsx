import { useMemo, useCallback } from "react";
import Header from "../components/studio/Header";
import UploadPanel from "../components/studio/UploadPanel";
import AnnotationPanel from "../components/studio/AnnotationPanel";
import PromptInput from "../components/studio/PromptInput";
import GenerateButton from "../components/studio/GenerateButton";
import ProgressIndicator from "../components/studio/ProgressIndicator";
import ComparisonView from "../components/studio/ComparisonView";
import DownloadButton from "../components/studio/DownloadButton";
import { useStudioState, STATUS } from "../state/studioStore";
import { generateImage } from "../services/api";

export default function StudioPage() {
  const studio = useStudioState();

  const handleImageChange = useCallback(
    (newImage) => {
      studio.setImage(newImage);
      studio.setMask(null);
      studio.setResult(null);
      studio.setError(null);
      studio.setStatus(newImage ? STATUS.UPLOADED : STATUS.IDLE);
    },
    [studio]
  );

  const canGenerate = useMemo(() => {
    return (
      Boolean(studio.image) &&
      Boolean(studio.image.id) &&
      Boolean(studio.mask) &&
      studio.prompt.trim().length > 0 &&
      studio.status !== STATUS.GENERATING
    );
  }, [studio.image, studio.mask, studio.prompt, studio.status]);

  const handleGenerate = useCallback(async () => {
    if (!studio.image?.id || !studio.mask) return;

    studio.setStatus(STATUS.GENERATING);
    studio.setError(null);

    try {
      const result = await generateImage({
        imageId: studio.image.id,
        prompt: studio.prompt,
        maskDataUrl: studio.mask.dataUrl,
      });

      studio.setResult({ url: result.result_url, mask_url: result.mask_url });
      studio.setStatus(STATUS.COMPLETE);
    } catch (err) {
      studio.setError(err.message || "Generation failed.");
      studio.setStatus(STATUS.FAILED);
    }
  }, [studio]);

  return (
    <div className="min-h-screen bg-surface">
      <Header />

      <main className="mx-auto max-w-6xl px-4 py-6 sm:px-6 lg:py-8">
        <div className="grid grid-cols-1 gap-6 lg:grid-cols-[1.15fr_1fr]">
          <section className="flex flex-col gap-6">
            <UploadPanel image={studio.image} onImageChange={handleImageChange} />
            <AnnotationPanel
              image={studio.image}
              mask={studio.mask}
              onMaskChange={studio.setMask}
            />
          </section>

          <section className="flex flex-col gap-6">
            <PromptInput
              value={studio.prompt}
              onChange={studio.setPrompt}
              disabled={!studio.image}
            />
            <GenerateButton
              disabled={!canGenerate}
              status={studio.status}
              onClick={handleGenerate}
            />
            <ProgressIndicator status={studio.status} />
          </section>
        </div>

        <div className="mt-6">
        <ComparisonView
          originalUrl={studio.image?.previewUrl}
          resultUrl={studio.result?.mask_url || studio.result?.url}
        />
        </div>

        <div className="mt-6 flex justify-end">
          <DownloadButton resultUrl={studio.result?.url} disabled={!studio.result} />
        </div>
      </main>
    </div>
  );
}