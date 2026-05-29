import Link from "next/link";
import type { ContactListItem } from "@/shared/types/contact";

export function ContactListCard({ contact }: { contact: ContactListItem }) {
  return (
    <Link
      href={`/contacts/${contact.id}`}
      className="flex gap-3 rounded-xl border border-[var(--color-border)] bg-[var(--color-surface)] p-3 hover:border-[var(--color-primary)]"
    >
      {contact.image_url ? (
        // eslint-disable-next-line @next/next/no-img-element
        <img src={contact.image_url} alt="" className="h-20 w-14 shrink-0 rounded object-cover" />
      ) : (
        <div className="flex h-20 w-14 shrink-0 items-center justify-center rounded bg-[var(--color-primary-muted)] text-lg font-medium text-[var(--color-primary)]">
          {(contact.display_name ?? "?")[0]}
        </div>
      )}
      <div className="min-w-0 flex-1">
        <p className="font-medium text-[var(--color-text-primary)]">{contact.display_name ?? "未命名"}</p>
        <p className="text-sm text-[var(--color-text-secondary)]">{contact.company_name ?? "—"}</p>
        <p className="text-sm text-[var(--color-text-tertiary)]">{contact.title ?? "—"}</p>
        {contact.responsibility_scope && (contact.responsibility_confidence ?? 0) >= 0.6 ? (
          <p className="mt-1 line-clamp-1 text-xs text-[var(--color-ai-text)]">{contact.responsibility_scope}</p>
        ) : contact.company_enrichment_status === "pending" ? (
          <p className="mt-1 animate-pulse text-xs text-[var(--color-text-tertiary)]">⏳ 補全公司資訊中…</p>
        ) : contact.company_products_preview ? (
          <p className="mt-1 line-clamp-1 text-xs text-[var(--color-ai-text)]">{contact.company_products_preview}</p>
        ) : null}
        {contact.source_label && (
          <p className="mt-1 text-xs text-[var(--color-text-tertiary)]">{contact.source_label}</p>
        )}
      </div>
      {contact.review_status === "unconfirmed" && (
        <span className="self-start rounded bg-[var(--color-accent-muted)] px-1.5 py-0.5 text-[10px] font-medium text-[var(--color-accent-hover)]">
          待確認
        </span>
      )}
    </Link>
  );
}
