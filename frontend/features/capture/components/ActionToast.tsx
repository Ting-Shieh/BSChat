"use client";

export function ActionToast({ message }: { message: string | null }) {
  if (!message) return null;
  return (
    <div className="fixed bottom-20 left-1/2 z-50 -translate-x-1/2 rounded-full bg-[var(--color-text-primary)] px-4 py-2 text-sm text-white shadow-lg">
      {message}
    </div>
  );
}
