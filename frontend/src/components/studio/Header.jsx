export default function Header() {
  return (
    <header className="border-b border-gray-200 bg-white">
      <div className="mx-auto flex max-w-6xl items-center justify-between px-4 py-4 sm:px-6">
        <div className="flex items-center gap-2">
          <div className="flex h-9 w-9 items-center justify-center rounded-card bg-primary font-bold text-white">
            C
          </div>
          <div>
            <h1 className="text-lg font-semibold leading-tight text-text-primary">
              CrumbleVision AI
            </h1>
            <p className="text-xs leading-tight text-text-secondary">
              Synthetic Defect Generation Studio
            </p>
          </div>
        </div>
        <span className="hidden rounded-full border border-gray-200 bg-surface px-3 py-1 text-xs font-medium text-text-secondary sm:inline-flex">
          MVP
        </span>
      </div>
    </header>
  );
}