"use client";

import Link from "next/link";
import { useCopyContact, CopyToast } from "@/features/actions";
import { ContactPreviewCard } from "@/shared/components/ContactPreviewCard";
import type { SearchResultItem } from "@/shared/types/search";

export function SearchResultCard({
  item,
  queryId,
}: {
  item: SearchResultItem;
  queryId: string;
}) {
  const { copy, message } = useCopyContact();
  const preview = item.contact_preview;
  const phone = preview.phones[0];
  const email = preview.emails[0];

  return (
    <article className="rounded-xl border border-[var(--color-border)] bg-[var(--color-surface)] p-4">
      <Link href={`/contacts/${item.contact_id}?from_search=${queryId}&rank=${item.rank}`}>
        <div className="relative">
          <ContactPreviewCard preview={preview} />
          {preview.review_status === "unconfirmed" && (
            <span className="absolute right-0 top-0 rounded bg-[var(--color-accent-muted)] px-1.5 py-0.5 text-[10px] font-medium text-[var(--color-accent-hover)]">
              未確認
            </span>
          )}
        </div>
      </Link>

      {(phone || email) && (
        <div className="mt-2 space-y-1 text-xs text-[var(--color-text-secondary)]">
          {phone && <p>📞 {phone}</p>}
          {email && <p>✉️ {email}</p>}
        </div>
      )}

      <p className="mt-3 rounded-lg bg-[var(--color-ai-bg)] px-3 py-2 text-sm text-[var(--color-ai-text)]">
        {item.match_reason}
      </p>

      {(phone || email) && (
        <div className="mt-3 flex flex-wrap items-center gap-2">
          {phone && (
            <button
              type="button"
              onClick={() => void copy(phone, "電話")}
              className="rounded-lg border border-[var(--color-border)] bg-[var(--color-surface)] px-3 py-1.5 text-xs font-medium text-[var(--color-primary)] hover:border-[var(--color-primary)]"
              aria-label={`複製 ${preview.display_name ?? "聯絡人"} 的電話`}
            >
              📋 複製電話
            </button>
          )}
          {email && (
            <button
              type="button"
              onClick={() => void copy(email, "Email")}
              className="rounded-lg border border-[var(--color-border)] bg-[var(--color-surface)] px-3 py-1.5 text-xs font-medium text-[var(--color-primary)] hover:border-[var(--color-primary)]"
              aria-label={`複製 ${preview.display_name ?? "聯絡人"} 的 Email`}
            >
              ✉️ 複製 Email
            </button>
          )}
          {message && (
            <span className="text-xs text-[var(--color-accent-hover)]" role="status">
              {message}
            </span>
          )}
        </div>
      )}
      <CopyToast message={message} />
    </article>
  );
}
