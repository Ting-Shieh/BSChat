import type { ContactPreview } from "@/shared/types/search";

export function ContactPreviewCard({
  preview,
  footer,
}: {
  preview: ContactPreview;
  footer?: React.ReactNode;
}) {
  return (
    <div className="flex gap-3">
      {preview.image_url ? (
        // eslint-disable-next-line @next/next/no-img-element
        <img src={preview.image_url} alt="" className="h-16 w-12 shrink-0 rounded object-cover" />
      ) : (
        <div className="flex h-16 w-12 shrink-0 items-center justify-center rounded bg-[var(--color-primary-muted)] text-sm font-medium text-[var(--color-primary)]">
          {(preview.display_name ?? "?")[0]}
        </div>
      )}
      <div className="min-w-0 flex-1">
        <p className="font-medium text-[var(--color-text-primary)]">{preview.display_name ?? "未命名"}</p>
        <p className="text-sm text-[var(--color-text-secondary)]">{preview.company_name ?? "—"}</p>
        <p className="text-sm text-[var(--color-text-tertiary)]">{preview.title ?? "—"}</p>
        {footer}
      </div>
    </div>
  );
}
