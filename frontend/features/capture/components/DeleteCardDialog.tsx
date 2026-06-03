"use client";

type DeleteCardDialogProps = {
  open: boolean;
  name: string;
  company: string;
  onCancel: () => void;
  onConfirm: () => void;
  pending?: boolean;
};

export function DeleteCardDialog({
  open,
  name,
  company,
  onCancel,
  onConfirm,
  pending = false,
}: DeleteCardDialogProps) {
  if (!open) return null;

  const summary = [name, company].filter(Boolean).join(" · ") || "這張名片";

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4">
      <div
        role="dialog"
        aria-labelledby="delete-card-title"
        className="w-full max-w-sm rounded-2xl bg-[var(--color-surface)] p-5 shadow-lg"
      >
        <h2 id="delete-card-title" className="text-lg font-semibold text-[var(--color-text-primary)]">
          刪除這張名片？
        </h2>
        <p className="mt-2 text-sm text-[var(--color-text-secondary)]">
          將從名片庫與待確認移除，之後搜尋不到這位聯絡人。
        </p>
        <p className="mt-3 rounded-lg bg-[var(--color-primary-muted)] px-3 py-2 text-sm text-[var(--color-text-primary)]">
          {summary}
        </p>
        <div className="mt-5 flex gap-3">
          <button
            type="button"
            onClick={onCancel}
            disabled={pending}
            className="flex-1 rounded-xl border border-[var(--color-border)] py-2.5 text-sm text-[var(--color-text-primary)]"
          >
            取消
          </button>
          <button
            type="button"
            onClick={onConfirm}
            disabled={pending}
            className="flex-1 rounded-xl bg-[var(--color-error)] py-2.5 text-sm font-medium text-white disabled:opacity-50"
          >
            {pending ? "刪除中…" : "刪除"}
          </button>
        </div>
      </div>
    </div>
  );
}
