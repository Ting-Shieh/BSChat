import Link from "next/link";
import type { ContactListItem } from "@/shared/types/contact";
import { resolveMediaUrl } from "@/shared/lib/media-url";

const DORMANT_THRESHOLD = 6;

export function ContactListCard({ contact }: { contact: ContactListItem }) {
  const imageSrc = resolveMediaUrl(contact.image_url);
  const dormant = contact.dormant_months ?? null;
  const isDormant = dormant !== null && dormant >= DORMANT_THRESHOLD;
  const initials = (contact.display_name ?? contact.company_name ?? "?").slice(0, 2);

  const aiPreview =
    contact.company_products_preview ||
    (contact.responsibility_scope && (contact.responsibility_confidence ?? 0) >= 0.6
      ? contact.responsibility_scope
      : null);

  return (
    <Link
      href={`/contacts/${contact.id}`}
      className="flex gap-3 rounded-xl border border-[var(--color-border)] bg-[var(--color-surface)] p-3 hover:border-[var(--color-primary)]"
    >
      {imageSrc ? (
        // eslint-disable-next-line @next/next/no-img-element
        <img src={imageSrc} alt="" className="h-[42px] w-[42px] shrink-0 rounded-[11px] object-cover" />
      ) : (
        <div className="flex h-[42px] w-[42px] shrink-0 items-center justify-center rounded-[11px] bg-[var(--color-primary-muted)] text-sm font-bold text-[var(--color-primary)]">
          {initials}
        </div>
      )}
      <div className="min-w-0 flex-1">
        <div className="flex items-start justify-between gap-2">
          <p className="font-semibold text-[15px] text-[var(--color-text-primary)]">
            {contact.display_name ?? "未命名"}
          </p>
          {isDormant && (
            <span className="shrink-0 rounded-full bg-[var(--color-accent-muted)] px-2 py-0.5 text-[10px] font-semibold text-[var(--color-accent-hover)]">
              💤 {dormant} 月
            </span>
          )}
          {!isDormant && contact.review_status === "unconfirmed" && (
            <span className="shrink-0 rounded bg-[var(--color-accent-muted)] px-1.5 py-0.5 text-[10px] font-medium text-[var(--color-accent-hover)]">
              待確認
            </span>
          )}
        </div>
        <p className="text-xs text-[var(--color-text-secondary)]">
          {[contact.company_name, contact.title].filter(Boolean).join(" · ") || "—"}
        </p>
        {contact.company_enrichment_status === "pending" ? (
          <p className="mt-1.5 animate-pulse text-[11.5px] text-[var(--color-text-tertiary)]">
            ✦ AI 辨識公司中…
          </p>
        ) : aiPreview ? (
          <p className="mt-1.5 line-clamp-1 border-l-[3px] border-[var(--color-ai-border)] bg-[var(--color-ai-bg)] py-1 pl-2 pr-2 text-[11.5px] leading-snug text-[var(--color-ai-text)]">
            {aiPreview}
          </p>
        ) : null}
        {contact.captured_by_name && (
          <p className="mt-1 text-[11px] text-[var(--color-text-tertiary)]">
            👤 由 {contact.captured_by_name} 收錄
          </p>
        )}
      </div>
    </Link>
  );
}
