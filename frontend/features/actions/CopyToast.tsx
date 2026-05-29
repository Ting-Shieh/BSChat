"use client";

export function CopyToast({ message }: { message: string | null }) {
  if (!message) return null;

  return (
    <div
      className="pointer-events-none fixed bottom-20 left-1/2 z-50 -translate-x-1/2 rounded-xl bg-[var(--color-text-primary)] px-4 py-2.5 text-sm font-medium text-white shadow-lg"
      role="status"
      aria-live="polite"
    >
      {message}
    </div>
  );
}
