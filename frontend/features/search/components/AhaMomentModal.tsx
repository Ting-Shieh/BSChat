"use client";

export function AhaMomentModal({ onClose }: { onClose: () => void }) {
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4">
      <div className="max-w-sm rounded-2xl bg-[var(--color-surface)] p-6 text-center shadow-lg">
        <p className="text-2xl">🎉</p>
        <h2 className="mt-2 text-lg font-semibold text-[var(--color-text-primary)]">找到了！</h2>
        <p className="mt-2 text-sm text-[var(--color-text-secondary)]">
          你的名片庫已經可以用對話式搜尋找回商機了。
        </p>
        <button
          type="button"
          onClick={onClose}
          className="mt-4 w-full rounded-xl bg-[var(--color-primary)] py-2.5 text-sm font-medium text-white"
        >
          太好了
        </button>
      </div>
    </div>
  );
}
